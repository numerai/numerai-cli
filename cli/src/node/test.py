import time
from datetime import datetime

import boto3
import requests
import numerapi

from cli.src.constants import *
from cli.src.util import docker
from cli.src.util.debug import exception_with_msg
from cli.src.util.files import load_or_init_nodes
from cli.src.util.keys import get_aws_keys

LOG_TYPE_WEBHOOK = 'webhook'
LOG_TYPE_CLUSTER = 'cluster'
LOG_TYPES = [
    LOG_TYPE_WEBHOOK,
    LOG_TYPE_CLUSTER
]


@click.command()
@click.option(
    '--local', '-l', type=str, default='',
    help=f'Test the container locally with a command.' \
         f' Defaults to the one specified in the Dockerfile.')
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def test(ctx, local, verbose):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    ctx.ensure_object(dict)
    node = ctx.obj['node']
    click.secho("checking if webhook is reachable...")
    node_config = load_or_init_nodes(node)

    if local != '':
        docker.build(node, verbose)
        docker.run(node_config['docker_repo'], verbose, command=local)

    napi = numerapi.NumerAPI()
    napi.raw_query()
    res = requests.post(
        node_config['webhook_url'],
        json={"roundNumber": -1, "dataVersion": -1}
    )
    res.raise_for_status()

    click.secho("webhook request successful...", fg='green')
    if verbose:
        click.echo(f"response:\n{res.json()}")
        click.secho(
            "You can now run `numerai compute status` or `numerai compute logs -f` "
            "to see your compute node running.", fg='yellow'
        )

    if node_config['provider'] == PROVIDER_AWS:
        task_info = get_latest_task_status_aws(verbose)

    else:
        click.secho(f"Unsupported provider: '{node_config['provider']}'", fg='red')
        return

    if task_info is None:
        raise exception_with_msg(
            "No tasks in the PENDING/RUNNING/STOPPED state found. "
            "This may mean that your task has been finished for a long time, and no longer exists. "
            "Check `numerai compute logs` and `numerai compute logs -l lambda` to see what happened.")

    task_id, task_status, task_date, _ = task_info
    click.echo("task ID: " + task_id)
    click.echo("status : " + task_status)
    click.echo("created: " + task_date)


def get_task_status_aws(ecs_client, task_arn, verbose):
    if verbose:
        click.echo(f"Getting task information for {task_arn}...")

    tasks = ecs_client.describe_tasks(
        cluster='numerai-submission',
        tasks=[task_arn])

    if not len(tasks['tasks']):
        if verbose:
            click.echo(f"Task not found...")
        return None

    task = tasks['tasks'][0]
    return task["taskArn"], task["lastStatus"], str(task["createdAt"]), task['desiredStatus']


# TODO: harden source of cluster arn string and make multi-node support?
def get_latest_task_status_aws(verbose):
    aws_public, aws_secret = get_aws_keys()
    ecs_client = boto3.client(
        'ecs', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)

    tasks = ecs_client.list_tasks(
        cluster='numerai-submission',
        desiredStatus="RUNNING")

    if verbose:
        click.echo(f"Found {len(tasks['taskArns'])} RUNNING tasks...")

    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(
            cluster='numerai-submission',
            desiredStatus="STOPPED")
        if verbose:
            click.echo(f"Found {len(tasks['taskArns'])} STOPPED tasks...")

    if len(tasks["taskArns"]) == 0:
        return None

    task = tasks["taskArns"][0]
    return get_task_status_aws(ecs_client, task, verbose)


def print_logs(logs_client, family, name, limit=None, next_token=None):

    kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
    if next_token is not None:
        kwargs['nextToken'] = next_token
    if limit is not None:
        kwargs['limit'] = limit

    events = logs_client.get_log_events(
        logGroupName=family,
        logStreamName=name,
        limit=limit)

    click.echo("log for " + family + ":" + name + ":")
    if len(events["events"]) == limit:
        click.echo('...more log lines available: use -n option to get more...')
    for event in events["events"]:
        click.echo(f"{str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}")

    return events['nextForwardToken']


def get_logs(verbose, num_lines, log_type, follow_tail, node):
    """
    Get the logs from the last run task

    Keep in mind, logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date
    """
    if log_type not in LOG_TYPES:
        raise exception_with_msg(f"Unknown log type '{log_type}', "
                                 f"must be one of {LOG_TYPES}")

    node_config = load_or_init_nodes(node)
    if node_config.provider == PROVIDER_AWS:
        get_logs_aws(node_config, num_lines, log_type, follow_tail, verbose)

    else:
        click.secho(f"Unsupported provider: '{node_config['provider']}'", fg='red')
        return


def get_logs_aws(node_config, num_lines, log_type, follow_tail, verbose):
    aws_public, aws_secret = get_aws_keys()
    logs_client = boto3.client(
        'logs', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)

    if log_type == LOG_TYPE_WEBHOOK:
        family = node_config['webhook_log_group']
        get_name_and_print_logs(logs_client, family, num_lines)
        return

    if log_type == LOG_TYPE_CLUSTER:
        family = node_config['cluster_log_group']

        task_info = get_latest_task_status_aws(verbose)
        if task_info is None or task_info[1] == 'STOPPED':
            get_name_and_print_logs(logs_client, family, num_lines)
            if task_info is not None and task_info[3] == 'RUNNING':
                return click.secho(
                    "there is another task in the PENDING state. Check its status with "
                    "`numerai compute status` and then rerun the logs command once it is RUNNING.", fg='red')

        task_arn, task_status, task_date, task_desired_status = task_info

        i = 0
        name = None
        while name is None:
            i += 1

            streams = logs_client.describe_log_streams(
                logGroupName=family,
                orderBy="LastEventTime",
                descending=True)

            for stream in streams['logStreams']:
                if stream['logStreamName'].endswith(task_arn.split('/')[-1]):
                    name = stream['logStreamName']
                    break

            click.secho(f"Log file has not been created yet. "
                        f"Waiting{'.'*i}\r", fg='yellow', nl=False)
            time.sleep(2)

        task_arn, task_status, task_date, _ = get_latest_task_status_aws(verbose)

        next_token = print_logs(logs_client, family, name, limit=num_lines)
        ecs_client = boto3.client(
            'ecs', region_name='us-east-1',
            aws_access_key_id=aws_public,
            aws_secret_access_key=aws_secret)
        while follow_tail:
            events = logs_client.get_log_events(
                logGroupName=family,
                logStreamName=name,
                nextToken=next_token)

            for event in events["events"]:
                click.echo(f"{str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}")

            task_arn, task_status, task_date, _ = get_task_status_aws(ecs_client, task_arn, verbose)
            if task_status != "RUNNING":
                click.secho(f"Task is now in the {task_status} state", fg='yellow')
                return
        return


def get_name_and_print_logs(logs_client, family, limit, next_token=None, raise_on_error=True):
    streams = logs_client.describe_log_streams(
        logGroupName=family,
        orderBy="LastEventTime",
        descending=True)

    if len(streams['logStreams']) == 0:
        if not raise_on_error:
            return False
        raise exception_with_msg(
            "No logs found. Make sure the webhook has triggered (check 'numerai compute logs -l lambda'). \n"
            "If it has, then check `numerai compute status` and make sure it's in the RUNNING state "
            "(this can take a few minutes). \n Also, make sure your webhook has triggered at least once by running "
            "'numerai compute test-webhook'")

    name = streams['logStreams'][0]['logStreamName']
    print_logs(logs_client, family, name, limit, next_token)
    return True


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--num-lines', '-n', type=int, default=20,
    help="the number of log lines to return")
@click.option(
    "--log-type", "-l", default="cluster",
    help=f"The log type to lookup. One of {LOG_TYPES}. Default is fargate")
@click.option(
    "--follow-tail", "-f", is_flag=True,
    help="tail the logs constantly")
@click.pass_context
def logs(ctx, verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the last run task

    Keep in mind, logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date
    """
    ctx.ensure_object(dict)
    node = ctx.obj['node']
    get_logs(verbose, num_lines, log_type, follow_tail, node)
