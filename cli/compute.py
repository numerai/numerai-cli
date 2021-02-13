import time
from datetime import datetime

import click
import boto3
import requests

from cli.doctor import exception_with_msg
from cli.configure import Config, PROVIDER_AWS


@click.group()
def compute():
    """Commands for inspecting your running compute node."""
    pass


@compute.command()
@click.option('--quiet', '-q', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def test_webhook(quiet, app):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    config = Config()

    round_json = {
        "roundNumber": -1,
        "dataVersion": 1
    }

    req = requests.post(config.webhook_url(app), json=round_json)

    req.raise_for_status()

    if not quiet:
        click.echo("request success")
        click.echo(req.json())

        click.secho("You can now run `numerai compute status` or `numerai compute logs -f` "
                    "to see your compute node running.", fg='yellow')


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


# TODO: harden source of cluster arn string and make multi-app support?
def get_latest_task_status_aws(config, app, verbose):
    ecs_client = boto3.client(
        'ecs', region_name='us-east-1',
        aws_access_key_id=config.aws_public,
        aws_secret_access_key=config.aws_secret)

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


@compute.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def status(verbose, app):
    """
    Get the status of the latest task in compute
    """
    config = Config()

    provider = config.provider(app)
    if provider == PROVIDER_AWS:
        task_info = get_latest_task_status_aws(config, app, verbose)

    else:
        click.secho(f"Unsupported provider: '{provider}'", fg='red')
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
            "'curl `cat .numerai/submission_url.txt`'")

    name = streams['logStreams'][0]['logStreamName']
    print_logs(logs_client, family, name, limit, next_token)
    return True


def logs_aws(config, app, num_lines, log_type, follow_tail, verbose):
    logs_client = boto3.client(
        'logs', region_name='us-east-1',
        aws_access_key_id=config.aws_public,
        aws_secret_access_key=config.aws_secret)

    if log_type == "webhook":
        family = config.webhook_log_group(app)
        get_name_and_print_logs(logs_client, family, num_lines)

    elif log_type == "cluster":
        family = config.cluster_log_group(app)

        task_info = get_latest_task_status_aws(config, app, verbose)
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

        task_arn, task_status, task_date, _ = get_latest_task_status_aws(config, app, verbose)

        next_token = print_logs(logs_client, family, name, limit=num_lines)
        ecs_client = boto3.client(
            'ecs', region_name='us-east-1',
            aws_access_key_id=config.aws_public,
            aws_secret_access_key=config.aws_secret)
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


log_type_options = ['cluster', 'webhook']
@compute.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--num-lines', '-n', type=int, default=20,
    help="the number of log lines to return")
@click.option(
    "--log-type", "-l", default="cluster",
    help=f"The log type to lookup. One of {log_type_options}. Default is fargate")
@click.option(
    "--follow-tail", "-f", is_flag=True,
    help="tail the logs constantly")
@click.option(
    '--app', '-a', default='default',
    help="Target a different app other than 'default'")
def logs(verbose, num_lines, log_type, follow_tail, app):
    """
    Get the logs from the last run task

    Keep in mind, logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date
    """
    if log_type not in log_type_options:
        raise exception_with_msg(f"Unknown log type '{log_type}', must be one of {log_type_options}")

    config = Config()
    provider = config.provider(app)
    if provider == PROVIDER_AWS:
        logs_aws(config, app, num_lines, log_type, follow_tail, verbose)

    else:
        click.secho(f"Unsupported provider: '{provider}'", fg='red')
        return
