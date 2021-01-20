import time
from datetime import datetime

import click
import boto3
import requests
from colorama import Fore

from cli.doctor import exception_with_msg
from cli.configure import Config


@click.group()
def compute():
    """Commands for inspecting your running compute node."""
    pass


@compute.command()
@click.option('--quiet', '-q', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def test_webhook(quiet):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    config = Config()

    round_json = {
        "roundNumber": -1,
        "dataVersion": 1,
    }

    req = requests.post(config.webhook_url, json=round_json)

    req.raise_for_status()

    if not quiet:
        click.echo("request success")
        click.echo(req.json())

        click.echo(
            Fore.YELLOW +
            "You can now run `numerai compute status` or `numerai compute logs -f` to see your compute node running."
        )


def get_latest_task(config, verbose):
    ecs_client = boto3.client('ecs',
                              region_name='us-east-1',
                              aws_access_key_id=config.aws_public,
                              aws_secret_access_key=config.aws_secret)
    tasks = ecs_client.list_tasks(cluster='numerai-submission-ecs-cluster',
                                  desiredStatus="RUNNING")
    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(cluster='numerai-submission-ecs-cluster',
                                      desiredStatus="STOPPED")

    if len(tasks["taskArns"]) == 0:
        return None

    tasks = ecs_client.describe_tasks(cluster='numerai-submission-ecs-cluster',
                                      tasks=[tasks["taskArns"][0]])

    return tasks['tasks'][0]


@compute.command()
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def status(verbose):
    """
    Get the status of the latest task in compute
    """
    config = Config()

    task = get_latest_task(config, verbose)

    if task is None:
        raise exception_with_msg(
            "No tasks in the PENDING/RUNNING/STOPPED state found. This may mean that your task has been finished for a long time, and no longer exists. Check `numerai compute logs` and `numerai compute logs -l lambda` to see what happened."
        )

    click.echo("task ID: " + task["taskArn"])
    click.echo("status : " + task["lastStatus"])
    click.echo("created: " + str(task["createdAt"]))


@compute.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--num-lines', '-n', type=int, default=20,
    help="the number of log lines to return")
@click.option(
    "--log-type", "-l", default="fargate",
    help="the log type to lookup. Options are fargate|lambda. Default is fargate")
@click.option(
    "--follow-tail", "-f", is_flag=True,
    help="tail the logs constantly")
# @click.option(
#     '--app', '-a', default='default',
#     help="Target a different app other than 'default'")
def logs(verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the last run task

    Keep in mind, logs are not created until a task is in the RUNNING state, so the logs returned by this command might be out of date
    """
    def print_logs(events, limit):
        if len(events["events"]) == limit:
            click.echo(
                '...more log lines available: use -n option to get more...')
        for event in events["events"]:
            click.echo(
                str(datetime.fromtimestamp(event['timestamp'] / 1000)) + ':' +
                event['message'])

    def get_name_and_print_logs(logs_client,
                                family,
                                limit,
                                nextToken=None,
                                raise_on_error=True):
        streams = logs_client.describe_log_streams(logGroupName=family,
                                                   orderBy="LastEventTime",
                                                   descending=True)

        if len(streams['logStreams']) == 0:
            if not raise_on_error:
                return False
            raise exception_with_msg(
                "No logs found. Make sure the webhook has triggered (check 'numerai compute logs -l lambda'). \n\
                If it has, then check `numerai compute status` and make sure it's in the RUNNING state (this can take a few minutes). \n\
                Also, make sure your webhook has triggered at least once by running 'curl `cat .numerai/submission_url.txt`'"
            )
        name = streams['logStreams'][0]['logStreamName']

        kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
        if nextToken is not None:
            kwargs['nextToken'] = nextToken
        if limit is not None:
            kwargs['limit'] = limit
        events = logs_client.get_log_events(logGroupName=family,
                                            logStreamName=name,
                                            **kwargs)
        click.echo("log for " + family + ":" + name + ":")
        print_logs(events, limit)
        return True

    config = Config()

    logs_client = boto3.client('logs',
                               region_name='us-east-1',
                               aws_access_key_id=config.aws_public,
                               aws_secret_access_key=config.aws_secret)

    if log_type == "fargate":
        family = "/fargate/service/numerai-submission"
    elif log_type == "lambda":
        family = "/aws/lambda/numerai-submission"
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        return
    else:
        raise exception_with_msg(
            "Unknown log type, expected 'fargate' or 'lambda': got " +
            log_type)

    def latest_task_printer(task):
        if task is None:
            click.echo(Fore.RED + "task not found or is in the STOPPED state")
        elif task['desiredStatus'] == 'RUNNING' and task[
                'lastStatus'] != 'RUNNING':
            click.echo(
                Fore.RED +
                "there is another task in the PENDING state. Check its status with `numerai compute status` and then rerun the logs command once it is RUNNING."
            )

    def task_status(task):
        ecs_client = boto3.client('ecs',
                                  region_name='us-east-1',
                                  aws_access_key_id=config.aws_public,
                                  aws_secret_access_key=config.aws_secret)
        resp = ecs_client.describe_tasks(
            cluster='numerai-submission-ecs-cluster', tasks=[task["taskArn"]])

        tasks = resp['tasks']
        if len(tasks) == 0:
            return None
        return tasks[0]

    def get_log_for_task_id(task_id):
        streams = logs_client.describe_log_streams(logGroupName=family,
                                                   orderBy="LastEventTime",
                                                   descending=True)

        for stream in streams['logStreams']:
            if stream['logStreamName'].endswith(task_id):
                return stream['logStreamName']
        return None

    task = get_latest_task(config, verbose)
    if task is None:
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        return

    status = task_status(task)
    if status is None or status["lastStatus"] == "STOPPED":
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        latest_task_printer(task)
        return

    task_id = task["taskArn"].split('/')[-1]

    name = get_log_for_task_id(task_id)
    if name is None:
        print("Log file has not been created yet. Waiting.", end='')
    while name is None:
        print('.', end='')
        time.sleep(2)
        name = get_log_for_task_id(task_id)

    task = get_latest_task(config, verbose)
    events = logs_client.get_log_events(logGroupName=family,
                                        logStreamName=name,
                                        limit=num_lines)

    click.echo("log for " + family + ":" + name + ":")
    print_logs(events, num_lines)

    if follow_tail:
        while True:
            events = logs_client.get_log_events(
                logGroupName=family,
                logStreamName=name,
                nextToken=events['nextForwardToken'])
            for event in events["events"]:
                click.echo(
                    str(datetime.fromtimestamp(event['timestamp'] / 1000)) +
                    ':' + event['message'])
            status = task_status(task)["lastStatus"]
            if status != "RUNNING":
                click.echo(Fore.YELLOW + "Task is now in the " + status +
                           " state")
                return
