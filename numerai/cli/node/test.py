import time
import json
from datetime import datetime

import boto3
import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util import docker
from numerai.cli.util.debug import exception_with_msg
from numerai.cli.util.files import load_or_init_nodes
from numerai.cli.util.keys import get_aws_keys, get_numerai_keys


@click.command()
@click.option(
    '--local', '-l', type=str, is_flag=True,
    help=f'Test the container locally, uses value specified with --command. ')
@click.option(
    '--command', '-c', type=str, default="",
    help=f'Used to override the terminal command during local testing. '
         f'Defaults to the command specified in the Dockerfile.')
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def test(ctx, local, command, verbose):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    node_config = load_or_init_nodes(node)

    if local:
        click.secho("starting local test; building container...")
        docker.build(node_config, verbose)
        click.secho("running container...")
        docker.run(node_config, verbose, command=command)

    napi = base_api.Api(*get_numerai_keys())
    try:
        click.secho("checking if webhook is reachable...")
        res = napi.raw_query(
            '''
            mutation ( $modelId: String! ) {
                triggerModelWebhook( modelId: $modelId )
            }
            ''',
            variables={
                'modelId': node_config['model_id'],
            },
            authorization=True
        )
        if verbose:
            click.echo(f"response:\n{res}")

    except ValueError as e:
        click.secho(f'there was a problem calling your webhook: {str(e)}', fg='red')
        if 'Internal Server Error' in str(e):
            click.secho('attempting to dump webhook logs', fg='red')
            monitor(node, node_config, True, 20, LOG_TYPE_WEBHOOK, False)
        return

    click.secho("webhook reachable checking task status...", fg='green')
    monitor(node, node_config, verbose, 15, LOG_TYPE_CLUSTER, follow_tail=True)

    click.secho("test complete", fg='green')


def monitor(node, config, verbose, num_lines, log_type, follow_tail):
    if log_type not in LOG_TYPES:
        raise exception_with_msg(f"Unknown log type '{log_type}', "
                                 f"must be one of {LOG_TYPES}")

    if config['provider'] == PROVIDER_AWS:
        monitor_aws(node, config, num_lines, log_type, follow_tail, verbose)

    else:
        click.secho(f"Unsupported provider: '{config['provider']}'", fg='red')
        return


def monitor_aws(node, config, num_lines, log_type, follow_tail, verbose):
    aws_public, aws_secret = get_aws_keys()
    logs_client = boto3.client(
        'logs', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)
    ecs_client = boto3.client(
        'ecs', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)

    if log_type == LOG_TYPE_WEBHOOK:
        family = config['webhook_log_group']
        get_name_and_print_logs(logs_client, family, num_lines)
        return

    if log_type == LOG_TYPE_CLUSTER:
        family = config['cluster_log_group']

        # wait until log stream has been created
        i = 0
        name = None
        while name is None:
            i += 1
            task = get_recent_task_status_aws(ecs_client, node, verbose)
            if task is None:
                get_name_and_print_logs(logs_client, family, num_lines)
                return
            task_id = task["taskArn"].split('/')[-1]

            streams = logs_client.describe_log_streams(
                logGroupName=family,
                logStreamNamePrefix=f"ecs/{node}/{task_id}"
            )
            streams = list(filter(
                lambda s: s['logStreamName'].endswith(task_id),
                streams['logStreams']
            ))

            msg = f"Task status: {task['lastStatus']}. "
            if len(streams) == 0:
                msg += f"Waiting for log file to be created...{'.' * i}\r"
                click.secho(msg, fg='yellow', nl=False)
                time.sleep(2)

            else:
                name = streams[0]['logStreamName']
                msg = f"\n{msg} Log file created: {name}"
                click.secho(msg, fg='green')
                break


        # print out the logs
        next_token, num_events = print_logs(logs_client, family, name, limit=num_lines)
        total_events = num_events
        while follow_tail:
            next_token, num_events = print_logs(
                logs_client, family, name,
                next_token=(next_token if total_events > 0 else None)
            )
            total_events += num_events
            if total_events == 0:
                click.secho(f"Waiting for log events...\r", fg='yellow', nl=False)

            task = get_recent_task_status_aws(ecs_client, node, verbose)

            if task['lastStatus'] == "STOPPED":
                click.secho(f"\nTask is stopping...", fg='yellow')

                if len(task['containers']) and 'exitCode' in task['containers'][0]:
                    container = task['containers'][0]
                    click.secho(f"Container Exit code: {container['exitCode']}", fg='red')
                    click.secho(f'Reason: {container["reason"]}', fg='red')

                break

        if total_events == 0:
            while total_events == 0:
                click.secho(f"No log events yet, still waiting...\r", fg='yellow', nl=False)
                next_token, num_events = print_logs(logs_client, family, name)
                total_events += num_events

        return


# TODO: harden source of cluster arn
def get_recent_task_status_aws(ecs_client, node, verbose):
    tasks = ecs_client.list_tasks(
        cluster='numerai-submission',
        family=node)

    # try to find stopped tasks
    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(
            cluster='numerai-submission',
            desiredStatus='STOPPED',
            family=node)

    if len(tasks["taskArns"]) == 0:
        click.secho(f"No recent tasks found...", fg='red')
        return None

    tasks = ecs_client.describe_tasks(
        cluster='numerai-submission',
        tasks=tasks["taskArns"]
    )
    return tasks['tasks'][0]


def get_name_and_print_logs(logs_client, family, limit, next_token=None, raise_on_error=True):
    streams = logs_client.describe_log_streams(
        logGroupName=family,
        orderBy="LastEventTime",
        descending=True)

    if len(streams['logStreams']) == 0:
        if not raise_on_error:
            return False
        raise exception_with_msg(
            "No logs found. Make sure the webhook has triggered by checking "
            "'numerai node status' and make sure a task is in the RUNNING state "
            "(this can take a few minutes). Also, make sure your webhook has "
            "triggered at least once by running 'numerai node test'")

    name = streams['logStreams'][0]['logStreamName']
    print_logs(logs_client, family, name, limit, next_token)
    return True


def print_logs(logs_client, family, name, limit=None, next_token=None):
    kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
    if next_token is not None:
        kwargs['nextToken'] = next_token
    if limit is not None:
        kwargs['limit'] = limit

    events = logs_client.get_log_events(
        logGroupName=family,
        logStreamName=name,
        **kwargs
    )

    if len(events["events"]) == limit:
        click.echo('...more log lines available: use -n option to get more...')
    for event in events["events"]:
        click.echo(f"[{name}] {str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}")

    return events['nextForwardToken'], len(events['events'])


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--num-lines', '-n', type=int, default=20,
    help="the number of log lines to return")
@click.option(
    "--log-type", "-l", type=click.Choice(LOG_TYPES), default=LOG_TYPE_CLUSTER,
    help=f"The log type to lookup. One of {LOG_TYPES}. Default is {LOG_TYPE_CLUSTER}.")
@click.option(
    "--follow-tail", "-f", is_flag=True,
    help="tail the logs constantly")
@click.pass_context
def status(ctx, verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the latest task

    Logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    monitor(node, load_or_init_nodes(node), verbose, num_lines, log_type, follow_tail)
