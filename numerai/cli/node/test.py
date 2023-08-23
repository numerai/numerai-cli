import time
import json
from datetime import datetime, timedelta

import boto3
import click
import requests
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util import docker
from numerai.cli.util.debug import exception_with_msg
from numerai.cli.util.files import load_or_init_nodes
from numerai.cli.util.keys import get_aws_keys, get_numerai_keys, get_azure_keys

from azure.identity import ClientSecretCredential
from azure.mgmt.storage import StorageManagementClient
from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import json


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
            if provider == "aws":
                trigger_id = res["data"]["triggerModelWebhook"]
            elif provider == "azure":
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
    monitor(node, node_config, verbose, 15, LOG_TYPE_CLUSTER, follow_tail=True)
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
        filter(
            lambda sub: sub["round"]["number"] == curr_round, res["data"]["submissions"]
        ),
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


def monitor(node, config, verbose, num_lines, log_type, follow_tail):
    if log_type not in LOG_TYPES:
        raise exception_with_msg(
            f"Unknown log type '{log_type}', " f"must be one of {LOG_TYPES}"
        )

    if config["provider"] == PROVIDER_AWS:
        monitor_aws(node, config, num_lines, log_type, follow_tail, verbose)
    elif config["provider"] == PROVIDER_AZURE:
        monitor_azure(node, config, verbose)
    else:
        click.secho(f"Unsupported provider: '{config['provider']}'", fg="red")
        return


def monitor_aws(node, config, num_lines, log_type, follow_tail, verbose):
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

    if log_type == LOG_TYPE_WEBHOOK:
        get_name_and_print_logs(logs_client, config["api_log_group"], num_lines)
        get_name_and_print_logs(logs_client, config["webhook_log_group"], num_lines)
        return

    if log_type == LOG_TYPE_CLUSTER:
        family = config["cluster_log_group"]

        # wait until log stream has been created
        i = 0
        name = None
        while name is None:
            i += 1
            task = get_recent_task_status_aws(ecs_client, node, verbose)
            if task is None:
                get_name_and_print_logs(logs_client, family, num_lines)
                return
            task_id = task["taskArn"].split("/")[-1]

            streams = logs_client.describe_log_streams(
                logGroupName=family, logStreamNamePrefix=f"ecs/{node}/{task_id}"
            )
            streams = list(
                filter(
                    lambda s: s["logStreamName"].endswith(task_id),
                    streams["logStreams"],
                )
            )

            msg = f"Task status: {task['lastStatus']}."

            if task["lastStatus"] == "STOPPED":
                if len(streams) == 0:
                    click.secho(f"{msg} No log file, did you deploy?", fg="yellow")
                    exit(1)
                else:
                    click.secho(f"{msg} Checking for log events...", fg="green")
                    break

            elif len(streams) == 0:
                click.secho(
                    f"{msg} Waiting for log file to be created..." f"{'.' * i}\r",
                    fg="yellow",
                    nl=False,
                )
                time.sleep(2)

            else:
                name = streams[0]["logStreamName"]
                click.secho(f"\n{msg} Log file created: {name}", fg="green")
                break

        # print out the logs
        next_token, num_events = print_logs(logs_client, family, name, limit=num_lines)
        total_events = num_events
        while follow_tail:
            next_token, num_events = print_logs(
                logs_client,
                family,
                name,
                next_token=(next_token if total_events > 0 else None),
            )
            total_events += num_events
            if total_events == 0:
                click.secho("Waiting for log events...\r", fg="yellow", nl=False)

            task = get_recent_task_status_aws(ecs_client, node, verbose)

            if task["lastStatus"] == "STOPPED":
                click.secho("\nTask is stopping...", fg="yellow")

                if len(task["containers"]) and "reason" in task["containers"][0]:
                    container = task["containers"][0]
                    click.secho(
                        f"Container Exit code: {container['exitCode']}\n"
                        f"Reason: {container['reason']}",
                        fg="red",
                    )
                break

        start = time.time()
        if total_events == 0:
            while total_events == 0:
                click.secho(
                    "No log events yet, still waiting...\r", fg="yellow", nl=False
                )
                next_token, num_events = print_logs(logs_client, family, name)
                total_events += num_events
                if (time.time() - start) > 60 * 5:
                    click.secho(
                        f"\nTimeout after 5 minutes, please run the `numerai node status`"
                        f"command for this model or visit the log console:\n"
                        f"https://console.aws.amazon.com/cloudwatch/home?"
                        f"region=us-east-1#logsV2:log-groups/log-group/$252Ffargate$252Fservice$252F{node}"
                        f"/log-events/{name.replace('/', '$252F')}",
                        fg="red",
                    )
                    break

        return


# TODO: harden source of cluster arn
def get_recent_task_status_aws(ecs_client, node, verbose):
    tasks = ecs_client.list_tasks(cluster="numerai-submission", family=node)

    # try to find stopped tasks
    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(
            cluster="numerai-submission", desiredStatus="STOPPED", family=node
        )

    if len(tasks["taskArns"]) == 0:
        click.secho(f"No recent tasks found...", fg="red")
        return None

    tasks = ecs_client.describe_tasks(
        cluster="numerai-submission", tasks=tasks["taskArns"]
    )
    return tasks["tasks"][0]


def get_name_and_print_logs(
    logs_client, family, limit, next_token=None, raise_on_error=True
):
    streams = logs_client.describe_log_streams(
        logGroupName=family, orderBy="LastEventTime", descending=True
    )

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
    print_logs(logs_client, family, name, limit, next_token)
    return True


def print_logs(logs_client, family, name, limit=None, next_token=None):
    kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
    if next_token is not None:
        kwargs["nextToken"] = next_token
    if limit is not None:
        kwargs["limit"] = limit

    events = logs_client.get_log_events(
        logGroupName=family, logStreamName=name, **kwargs
    )

    if len(events["events"]) == limit:
        click.echo("...more log lines available: use -n option to get more...")
    for event in events["events"]:
        click.echo(
            f"[{name}] {str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}"
        )

    return events["nextForwardToken"], len(events["events"])


def monitor_azure(node, config, verbose):
    """
    Monitor the logs of a node on Azure to see if the submission is completed
    """

    # Go get the log for all webhook calls started in the last 1 minutes
    monitor_start_time = datetime.now(timezone.utc) - timedelta(minutes=1)

    azure_subs_id, azure_client, azure_tenant, azure_secret = get_azure_keys()
    credentials = ClientSecretCredential(
        client_id=azure_client, tenant_id=azure_tenant, client_secret=azure_secret
    )
    # Get Azure Storage account key, using resource group name and trigger function's storage account name

    resource_group_name = config["resource_group_name"]
    storage_account_name = config["webhook_storage_account_name"]
    storage_client = StorageManagementClient(
        credential=credentials, subscription_id=azure_subs_id
    )
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
    table_service_client = TableServiceClient(
        endpoint=endpoint, credential=table_credential
    )
    table_name = [
        table.name
        for table in table_service_client.list_tables()
        if "History" in table.name
    ][0]

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


def azure_refresh_and_print_log(
    table_client, monitor_start_time, shown_log_row_key=list()
):
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
                click.secho(
                    f"Azure Trigger Function: '{az_func_name1}' started", fg="green"
                )
                # execute_st=log_df.loc[i,'_Timestamp']
            elif log_df.loc[i, "EventType"] == "ExecutionCompleted":
                az_func_name1 = execution_log.loc[
                    execution_log["EventType"] == "ExecutionStarted", "Name"
                ].values[0]
                execute_st = execution_log.loc[
                    execution_log["EventType"] == "ExecutionStarted", "_Timestamp"
                ].values[-1]
                execute_et = execution_log.loc[
                    execution_log["EventType"] == "ExecutionCompleted", "_Timestamp"
                ].values[-1]
                time_taken = execute_et - execute_st
                click.secho(
                    f"Azure Trigger Function: '{az_func_name1}' ended", fg="green"
                )
                click.secho(
                    f"'{az_func_name1}' time taken: {time_taken.astype('timedelta64[s]').astype('float')/60:.2f} mins"
                )
                click.secho(f"'{az_func_name1}' result: {log_df.loc[i,'Result']}")
                monitoring_done = True

    return monitoring_done, shown_log_row_key


@click.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--num-lines", "-n", type=int, default=20, help="the number of log lines to return"
)
@click.option(
    "--log-type",
    "-l",
    type=click.Choice(LOG_TYPES),
    default=LOG_TYPE_CLUSTER,
    help=f"The log type to lookup. One of {LOG_TYPES}. Default is {LOG_TYPE_CLUSTER}.",
)
@click.option("--follow-tail", "-f", is_flag=True, help="tail the logs constantly")
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
