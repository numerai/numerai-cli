import time
import json
from datetime import datetime, timedelta

import boto3
import botocore
import click
import requests
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util import docker
from numerai.cli.util.debug import exception_with_msg
from numerai.cli.util.files import load_or_init_nodes
from numerai.cli.util.keys import get_aws_keys, get_numerai_keys, get_azure_keys, get_gcp_keys

from azure.identity import ClientSecretCredential
from azure.mgmt.storage import StorageManagementClient
from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import json
import google.cloud.run_v2 as run_v2
import google.cloud.logging_v2 as logging_v2


@click.command()
@click.option(
    "--local",
    "-l",
    type=str,
    is_flag=True,
    help="Test the container locally, uses value specified with --command. ",
)
@click.option(
    "--command",
    "-c",
    type=str,
    default="",
    help="Used to override the terminal command during local testing. "
    "Defaults to the command specified in the Dockerfile.",
)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def test(ctx, local, command, verbose):
    """
    Full end-to-end cloud or local test for a Prediction Node.

    This checks that:
    1. Numerai can reach the Trigger
    2. The Trigger schedules a Container to run
    3. The Container starts up on the Compute Cluster
    4. The Container uploads a submission with the Trigger ID assigned to it
    """
    ctx.ensure_object(dict)
    model = ctx.obj["model"]
    node = model["name"]
    is_signals = model["is_signals"]
    node_config = load_or_init_nodes(node)
    provider = node_config["provider"]

    if local:
        click.secho("starting local test; building container...")
        docker.build(node_config, node, verbose)

        click.secho("running container...")
        docker.run(node_config, verbose, command=command)

    api = base_api.Api(*get_numerai_keys())
    trigger_id = None
    try:
        if "cron" in node_config:
            click.secho("Attempting to manually trigger Cron node...")
            res = requests.post(node_config["webhook_url"], json.dumps({}))
            res.raise_for_status()

        else:
            click.secho("Checking if Numerai can Trigger your model...")
            res = api.raw_query(
                """mutation ( $modelId: String! ) {
                    triggerModelWebhook( modelId: $modelId )
                }""",
                variables={
                    "modelId": node_config["model_id"],
                },
                authorization=True,
            )
            if provider in PROVIDERS:
                trigger_id = res["data"]["triggerModelWebhook"]
            else:
                click.secho(f"Unsupported provider: '{provider}'", fg="red")
                exit(1)
            click.secho(f"Trigger ID assigned for this test: {trigger_id}", fg="green")

        if verbose:
            click.echo(f"response:\n{res}")
        click.secho("Webhook reachable...", fg="green")

    except ValueError as e:
        click.secho("there was a problem calling your webhook...", fg="red")
        if "Internal Server Error" in str(e):
            click.secho("attempting to dump webhook logs", fg="red")
            monitor(node, node_config, True, 20, LOG_TYPE_WEBHOOK, False)
        return

    click.secho("checking task status...")
    monitor(node, node_config, verbose, 15, LOG_TYPE_CLUSTER, follow_tail=True, trigger_id=trigger_id)
    if node_config["provider"] == "azure":
        time.sleep(5)

    if node_config["provider"] == "azure":
        click.secho(
            "[Azure node] Test complete, your model should submits automatically! "
            "You may check your submission here: https://numer.ai/models",
            fg="green",
        )
        return

    click.secho("checking for submission...")
    res = api.raw_query(
        """query ( $modelId: String! ) {
            submissions( modelId: $modelId ){
                round{ number, tournament },
                triggerId
                insertedAt
            }
        }""",
        variables={"modelId": node_config["model_id"]},
        authorization=True,
    )
    tournament = TOURNAMENT_SIGNALS if is_signals else TOURNAMENT_NUMERAI
    curr_round = api.get_current_round(tournament)
    latest_subs = sorted(
        filter(lambda sub: sub["round"]["number"] == curr_round, res["data"]["submissions"]),
        key=lambda sub: sub["insertedAt"],
        reverse=True,
    )
    if len(latest_subs) == 0:
        click.secho("No submission found for current round, test failed", fg="red")
        return

    latest_sub = latest_subs[0]

    if "cron" in node_config:
        latest_date = datetime.strptime(latest_sub["insertedAt"], "%Y-%m-%dT%H:%M:%SZ")
        if latest_date < datetime.utcnow() - timedelta(minutes=5):
            click.secho(
                "No submission appeared in the last 5 minutes, be sure that your node"
                " is submitting correctly, check the numerai-cli wiki for more"
                " information on how to monitor parts of your node.",
                fg="red",
            )

    if trigger_id != latest_sub["triggerId"]:
        click.secho(
            "Your node did not submit the Trigger ID assigned during this test, "
            "please ensure your node uses numerapi >= 0.2.4 (ignore if using rlang or Azure as provider)",
            fg="red",
        )
        return

    click.secho("Submission uploaded correctly", fg="green")
    click.secho("Test complete, your model now submits automatically!", fg="green")


def monitor(node, config, verbose, num_lines, log_type, follow_tail, trigger_id=None):
    if log_type not in LOG_TYPES:
        raise exception_with_msg(f"Unknown log type '{log_type}', " f"must be one of {LOG_TYPES}")

    if config["provider"] == PROVIDER_AWS:
        monitor_aws(node, config, num_lines, log_type, follow_tail, verbose, trigger_id)
    elif config["provider"] == PROVIDER_AZURE:
        monitor_azure(node, config, verbose)
    elif config["provider"] == PROVIDER_GCP:
        monitor_gcp(node, config, verbose, log_type, trigger_id)
    else:
        click.secho(f"Unsupported provider: '{config['provider']}'", fg="red")
        return


def monitor_aws(node, config, num_lines, log_type, follow_tail, verbose, trigger_id):
    aws_public, aws_secret = get_aws_keys()
    logs_client = boto3.client(
        "logs",
        region_name="us-east-1",
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret,
    )
    ecs_client = boto3.client(
        "ecs",
        region_name="us-east-1",
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret,
    )

    monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    next_token = None
    log_lines = 0
    monitoring_done = False
    time_lapse = datetime.now(timezone.utc) - monitor_start_time
    task = None

    if verbose and log_type == LOG_TYPE_WEBHOOK:
        print_aws_webhook_logs(logs_client, config["webhook_log_group"], num_lines)

    while time_lapse <= timedelta(minutes=15) and monitoring_done == False:
        task, monitoring_done, message, color = get_recent_task_status_aws(
            config["cluster_arn"], ecs_client, node, trigger_id
        )
        if task is None:
            click.secho(message, fg=color)
        else:
            if verbose and log_type == LOG_TYPE_CLUSTER:
                next_token, new_log_lines = print_aws_logs(
                    logs_client,
                    config["cluster_log_group"],
                    f'ecs/default/{task["taskArn"].split("/")[-1]}',
                    next_token=next_token,
                    fail_on_not_found=False,
                )
                log_lines += new_log_lines
                if log_lines == 0:
                    next_token = None
            else:
                click.secho(message, fg=color)

        if not monitoring_done:
            time.sleep(5 if verbose else 15)
            time_lapse = datetime.now(timezone.utc) - monitor_start_time

    if monitoring_done and time_lapse <= timedelta(minutes=15) and verbose and log_lines == 0 and task is not None:
        click.secho(
            "Node executed successfully, but there are no logs yet.\n"
            "You can safely exit at this time, or the  CLI will try to collect logs for the next 120 seconds.",
            fg="yellow",
        )
        log_monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=0)
        log_time_lapse = datetime.now(timezone.utc) - log_monitor_start_time
        while log_time_lapse <= timedelta(minutes=2) and log_lines == 0:
            time.sleep(5)
            log_time_lapse <= datetime.now(timezone.utc) - log_monitor_start_time
            next_token, new_log_lines = print_aws_logs(
                logs_client,
                config["cluster_log_group"],
                f'ecs/default/{task["taskArn"].split("/")[-1]}',
                next_token=next_token,
                fail_on_not_found=False,
            )
            log_lines += new_log_lines
            if log_lines == 0:
                next_token = None

    elif time_lapse >= timedelta(minutes=15) and not monitoring_done:
        click.secho(
            f"\nTimeout after 5 minutes, please run the `numerai node status`"
            f"command for this model or visit the log console:\n"
            f"https://console.aws.amazon.com/cloudwatch/home?"
            f"region=us-east-1#logsV2:log-groups/log-group/$252Ffargate$252Fservice$252F{node}",
            fg="red",
        )


def get_recent_task_status_aws(cluster_arn, ecs_client, node, trigger_id):
    tasks = ecs_client.list_tasks(cluster=cluster_arn, family=node)

    pending_codes = ["PROVISIONING", "PENDING", "ACTIVATING"]
    running_codes = ["RUNNING", "DEACTIVATING", "STOPPING"]
    stopped_codes = ["DEPROVISIONING", "STOPPED", "DELETED"]

    # try to find stopped tasks
    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(cluster=cluster_arn, desiredStatus="STOPPED", family=node)

    if len(tasks["taskArns"]) == 0:
        message = "No recent tasks found!" if trigger_id is None else "No tasks yet, still waiting..."
        color = "red" if trigger_id is None else "yellow"
        return None, trigger_id is None, message, color

    tasks = ecs_client.describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])

    matched_task = None

    if trigger_id is not None:
        for task in tasks["tasks"]:
            matching_override = list(
                filter(lambda e: e["value"] == trigger_id, task["overrides"]["containerOverrides"][0]["environment"])
            )
            if len(matching_override) == 1:
                matched_task = task
                break
    else:
        matched_task = tasks["tasks"][-1]

    if matched_task == None:
        return matched_task, False, 'Waiting for job to start...', 'yellow'
    elif matched_task["lastStatus"] in stopped_codes and "reason" in matched_task["containers"][0]:
        return (
            matched_task,
            True,
            f'Job failed! Container exited with code {matched_task["containers"][0]["exitCode"]}\r',
            'red',
        )
    elif matched_task["lastStatus"] in stopped_codes:
        return matched_task, True, 'Job execution succeeded!\r', 'green'
    elif matched_task["lastStatus"] in pending_codes:
        return matched_task, False, 'Waiting for job to start...', 'yellow'
    elif matched_task["lastStatus"] in running_codes:
        return matched_task, False, 'Waiting for job to complete...', 'yellow'
    return matched_task, False, 'Waiting for job to start...', 'yellow'


def print_aws_webhook_logs(logs_client, family, limit, next_token=None, raise_on_error=True):
    streams = logs_client.describe_log_streams(logGroupName=family, orderBy="LastEventTime", descending=True)

    if len(streams["logStreams"]) == 0:
        if not raise_on_error:
            return False
        raise exception_with_msg(
            "No logs found. Make sure the webhook has triggered by checking "
            "`numerai node status` and make sure a task is in the RUNNING state "
            "(this can take a few minutes). Also, make sure your webhook has "
            "triggered at least once by running `numerai node test`"
        )

    name = streams["logStreams"][0]["logStreamName"]
    print_aws_logs(logs_client, family, name, limit, next_token)
    return True


def print_aws_logs(logs_client, family, name, limit=None, next_token=None, fail_on_not_found=True):
    kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
    if next_token is not None:
        kwargs["nextToken"] = next_token
    if limit is not None:
        kwargs["limit"] = limit
    try:
        events = logs_client.get_log_events(logGroupName=family, logStreamName=name, **kwargs)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceNotFoundException':
            if fail_on_not_found:
                raise error
            else:
                return None, 0
        else:
            raise error

    if len(events["events"]) == limit:
        click.echo("...more log lines available: use -n option to get more...")
    for event in events["events"]:
        click.echo(f"[{name}] {str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}")

    return events["nextForwardToken"], len(events["events"])


def monitor_azure(node, config, verbose):
    """
    Monitor the logs of a node on Azure to see if the submission is completed
    """

    # Go get the log for all webhook calls started in the last 1 minutes
    monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=1)

    azure_subs_id, azure_client, azure_tenant, azure_secret = get_azure_keys()
    credentials = ClientSecretCredential(client_id=azure_client, tenant_id=azure_tenant, client_secret=azure_secret)
    # Get Azure Storage account key, using resource group name and trigger function's storage account name

    resource_group_name = config["resource_group_name"]
    storage_account_name = config["webhook_storage_account_name"]
    storage_client = StorageManagementClient(credential=credentials, subscription_id=azure_subs_id)
    storage_keys = storage_client.storage_accounts.list_keys(
        resource_group_name=resource_group_name, account_name=storage_account_name
    )
    if len([keys for keys in storage_keys.keys]) == 0:
        click.secho(
            f"Webhook's storage account key not found, check storage account name: {storage_account_name}",
            fg="red",
        )
        exit(1)

    # Now we have the storage account's access keys
    storage_key = [keys for keys in storage_keys.keys][0]
    access_key = storage_key.value
    endpoint_suffix = "core.windows.net"
    account_name = storage_account_name
    endpoint = f"{account_name}.table.{endpoint_suffix}"
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={access_key};EndpointSuffix={endpoint_suffix}"

    # Get the table that store the run history for the webhook from the Azure storage account
    table_credential = AzureNamedKeyCredential(storage_account_name, access_key)
    table_service_client = TableServiceClient(endpoint=endpoint, credential=table_credential)
    table_name = [table.name for table in table_service_client.list_tables() if "History" in table.name][0]

    # Query the webhook's History table and get records (entities)
    table_client = TableClient.from_connection_string(connection_string, table_name)

    # Continue to query the table until the webhook's run is done (log printed) or 15 minutes have passed
    time_lapse = datetime.now(timezone.utc) - monitor_start_time
    monitoring_done = False
    shown_log_row_key = list()
    while time_lapse <= timedelta(minutes=15) and monitoring_done == False:
        if len(shown_log_row_key) == 0 and verbose:
            click.secho(f"No log events yet, still waiting...\r", fg="yellow")
        else:
            click.secho(
                f"Waiting for submission run to finish...\r",
                fg="yellow",
            )
        monitoring_done, shown_log_row_key = azure_refresh_and_print_log(
            table_client, monitor_start_time, shown_log_row_key
        )
        time.sleep(15)
        # Update time lapse
        time_lapse = datetime.now(timezone.utc) - monitor_start_time
    if time_lapse >= timedelta(minutes=15):
        click.secho(
            f"Monitor timeout after 15 minutes, container run status cannot be determined. Recommended to check ran status directly on Azure Portal",
            fg="red",
        )
        exit(1)


def azure_refresh_and_print_log(table_client, monitor_start_time, shown_log_row_key=list()):
    """
    Refresh the log table and print the new log entries
    """
    monitoring_done = False
    log_list = [entity for entity in table_client.list_entities()]
    if len(log_list) == 0:
        return monitoring_done, shown_log_row_key
    log_df = pd.DataFrame(log_list)
    relevant_cols = [
        "RowKey",
        "EventType",
        "_Timestamp",
        "Name",
        "OrchestrationInstance",
        "Result",
        "OrchestrationStatus",
    ]
    available_cols = [col for col in relevant_cols if col in log_df.columns]
    log_df = log_df[available_cols].dropna(subset=["EventType"])
    log_df = log_df[log_df["_Timestamp"] > monitor_start_time]
    execution_log = log_df[log_df["EventType"].str.contains("Execution")]

    # Remove logs that have been shown before
    log_df = log_df[log_df["RowKey"].isin(shown_log_row_key) == False].reset_index()

    if len(log_df) > 0:
        for i in range(len(log_df)):
            shown_log_row_key.append(log_df.loc[i, "RowKey"])

            if log_df.loc[i, "EventType"] == "ExecutionStarted":
                az_func_name1 = log_df.loc[i, "Name"]
                click.secho(f"Azure Trigger Function: '{az_func_name1}' started", fg="green")
                # execute_st=log_df.loc[i,'_Timestamp']
            elif log_df.loc[i, "EventType"] == "ExecutionCompleted":
                az_func_name1 = execution_log.loc[execution_log["EventType"] == "ExecutionStarted", "Name"].values[0]
                execute_st = execution_log.loc[execution_log["EventType"] == "ExecutionStarted", "_Timestamp"].values[
                    -1
                ]
                execute_et = execution_log.loc[execution_log["EventType"] == "ExecutionCompleted", "_Timestamp"].values[
                    -1
                ]
                time_taken = execute_et - execute_st
                click.secho(f"Azure Trigger Function: '{az_func_name1}' ended", fg="green")
                click.secho(
                    f"'{az_func_name1}' time taken: {time_taken.astype('timedelta64[s]').astype('float')/60:.2f} mins"
                )
                click.secho(f"'{az_func_name1}' result: {log_df.loc[i,'Result']}")
                monitoring_done = True

    return monitoring_done, shown_log_row_key


def monitor_gcp(node, config, verbose, log_type, trigger_id):
    ## Write a function that uses the gcloud runv2 executions SDK to get executions that are currently running
    monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=1)

    gcp_key_path = get_gcp_keys()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_key_path
    client = run_v2.ExecutionsClient()

    # Setup logging if necessary
    previous_insert_id = "0"
    logging_client = None
    if verbose:
        logging_client = logging_v2.Client()

    time_lapse = datetime.now(timezone.utc) - monitor_start_time
    monitoring_done = False

    if verbose and log_type == LOG_TYPE_WEBHOOK:
        print_gcp_webhook_logs(logging_client, config["job_id"])

    while time_lapse <= timedelta(minutes=15) and monitoring_done == False:
        executions = get_gcp_job_executions(client, config["job_id"], trigger_id)
        if len(executions) == 0:
            click.secho(f"No job executions yet, still waiting...\r", fg="yellow")
        else:
            monitoring_done, message, color = check_gcp_execution_status(executions[0])
            if verbose and log_type == LOG_TYPE_CLUSTER:
                previous_insert_id = print_gcp_execution_logs(
                    logging_client, config["job_id"], executions[0], previous_insert_id
                )
            elif not monitoring_done:
                click.secho(message, fg=color)

            if monitoring_done:
                click.secho(message, fg=color)
                break

        time.sleep(5 if verbose else 15)

    if time_lapse >= timedelta(minutes=15) and not monitoring_done:
        click.secho(
            f"Monitoring timed out after 15 minutes without determining the status of your container. Check the status of your container in the Google Cloud console.",
            fg="red",
        )
        exit(1)


def get_gcp_job_executions(client, job_id, trigger_id):
    # Initialize request argument(s)
    request = run_v2.ListExecutionsRequest(
        parent=job_id,
    )

    page_result = client.list_executions(request=request)
    executions = []
    # Handle the response
    for response in page_result:
        env = response.template.containers[0].env
        for env_var in env:
            if env_var.name == "TRIGGER_ID" and env_var.value == trigger_id:
                executions.append(response)
            elif trigger_id == None:
                executions.append(response)

    if trigger_id == None:
        executions = [executions[0]]
    return executions


def check_gcp_execution_status(execution):
    condition_based_results = {
        run_v2.types.Condition.State.CONDITION_SUCCEEDED: [True, "Job execution succeeded!\r", "green"],
        run_v2.types.Condition.State.CONDITION_RECONCILING: [False, "Waiting for job to complete...\r", "yellow"],
        run_v2.types.Condition.State.CONDITION_PENDING: [False, "Waiting for job to complete...\r", "yellow"],
        run_v2.types.Condition.State.CONDITION_FAILED: [False, "Job failed!\r", "red"],
    }

    completed_condition = list(filter(lambda c: c.type_ == "Completed", execution.conditions))
    if len(completed_condition) == 1:
        if completed_condition[0].state in list((condition_based_results.keys())):
            return condition_based_results[completed_condition[0].state]
        else:
            return True, f'Unknown job status! Exiting test.\nJob status: {completed_condition.state}\r', 'red'
    else:
        return False, "No job status found. Waiting for job status to resolve....\r", "yellow"


def print_gcp_execution_logs(logging_client, job_id, execution, previous_insert_id):
    execution_name = execution.name.split("/")[-1]

    filter = ' '.join(
        [
            'resource.type = "cloud_run_job"',
            f'resource.labels.job_name = "{job_id.split("/")[-1]}"',
            f'labels."run.googleapis.com/execution_name" = "{execution_name}"',
            'labels."run.googleapis.com/task_index" = "0"',
            f'insertId > "{previous_insert_id}"',
        ]
    )
    page_response = logging_client.list_entries(filter_=filter)
    insert_id = previous_insert_id
    for log in page_response:
        click.secho(f"{log.timestamp}: {log.payload}")
        insert_id = log.insert_id

    if insert_id == "0":
        click.secho(f"Waiting for logs to begin...\r", fg="yellow")

    return insert_id


def print_gcp_webhook_logs(logging_client, job_id):
    monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    click.secho("Looking for most recent webhook execution...\r", fg="yellow")

    filter = ' '.join(
        [
            'resource.type = "cloud_function"',
            f'resource.labels.function_name = "{job_id.split("/")[-1]}"',
            f'Timestamp>="{monitor_start_time.isoformat()}"',
        ]
    )

    page_response = logging_client.list_entries(filter_=filter)

    execution_id = ""
    log_entries = []
    for result in page_response:
        log_entries.append(
            {"payload": result.payload, "execution_id": result.labels["execution_id"], "timestamp": result.timestamp}
        )
        execution_id = result.labels["execution_id"]

    for log in log_entries:
        if log["execution_id"] == execution_id:
            click.secho(f"{log['timestamp']}: {log['payload']}")

    if len(log_entries) == 0:
        click.secho("No webhook logs in the past 30 minutes.\r", fg="yellow")
        click.secho(
            "Try executing your webhook again or run numerai node deploy to make sure your webhook URL is up to date\r",
            fg="yellow",
        )


@click.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option("--num-lines", "-n", type=int, default=20, help="the number of log lines to return")
@click.option(
    "--log-type",
    "-l",
    type=click.Choice(LOG_TYPES),
    default=LOG_TYPE_CLUSTER,
    help=f"The log type to lookup. One of {LOG_TYPES}. Default is {LOG_TYPE_CLUSTER}.",
)
@click.option("--follow-tail", "-f", is_flag=True, help="tail the logs of a running task (AWS only)")
@click.pass_context
def status(ctx, verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the latest task for this node

    Logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date.
    """
    ctx.ensure_object(dict)
    model = ctx.obj["model"]
    node = model["name"]
    monitor(node, load_or_init_nodes(node), verbose, num_lines, log_type, follow_tail)
