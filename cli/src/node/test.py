import time
from datetime import datetime

import boto3
import numerapi

from cli.src.constants import *
from cli.src.util import docker
from cli.src.util.debug import exception_with_msg
from cli.src.util.files import load_or_init_nodes
from cli.src.util.keys import get_aws_keys, get_numerai_keys

LOG_TYPE_WEBHOOK = 'webhook'
LOG_TYPE_CLUSTER = 'cluster'
LOG_TYPES = [
    LOG_TYPE_WEBHOOK,
    LOG_TYPE_CLUSTER
]


@click.command()
@click.option(
    '--local', '-l', type=str, is_flag=True,
    help=f'Test the container locally, uses value specified with --command. ')
@click.option(
    '--command', '-c', type=str, default="python predict.py",
    help=f'Used to override the terminal command during local testing. '
         f'Defaults to "python predict.py".')
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def test(ctx, local, command, verbose):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    ctx.ensure_object(dict)
    node = ctx.obj['node']
    click.secho("checking if webhook is reachable...")
    node_config = load_or_init_nodes(node)

    if local:
        docker.build(node_config, verbose)
        docker.run(node_config, verbose, command=command)

    napi = numerapi.NumerAPI(*get_numerai_keys())
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
                orderBy="LastEventTime",
                descending=True
            )
            streams = list(filter(
                lambda s: s['logStreamName'].endswith(task_id),
                streams['logStreams']
            ))
            if len(streams):
                name = streams[0]['logStreamName']
                break

            msg = (f"Task status: "
                   f"{task['lastStatus']} -> {task['desiredStatus']}. "
                   f"Waiting for log file to be created...{'.'*i}\r")
            click.secho(msg, fg='yellow', nl=False)
            time.sleep(2)

        # print out the logs
        click.secho('\ntask started and log file created', fg='green')
        next_token = print_logs(logs_client, family, name, limit=num_lines)
        while follow_tail:
            events = logs_client.get_log_events(
                logGroupName=family,
                logStreamName=name,
                nextToken=next_token)

            for event in events["events"]:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                click.echo(f"{str(timestamp)}: {event['message']}")

            task = get_recent_task_status_aws(ecs_client, node, verbose)
            if task['lastStatus'] == "STOPPED":
                click.secho(f"Task is stopping...", fg='yellow')
                break

        container = task['containers'][0]
        click.secho(f'Exit code: {container["exitCode"]}', fg='yellow')
        click.secho(f'Reason: {container["reason"]}', fg='yellow')

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
            "No logs found. Make sure the webhook has triggered (check 'numerai compute logs -l lambda'). \n"
            "If it has, then check `numerai compute status` and make sure it's in the RUNNING state "
            "(this can take a few minutes). \n Also, make sure your webhook has triggered at least once by running "
            "'numerai compute test-webhook'")

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
        limit=limit)

    click.echo("log for " + family + ":" + name + ":")
    if len(events["events"]) == limit:
        click.echo('...more log lines available: use -n option to get more...')
    for event in events["events"]:
        click.echo(f"{str(datetime.fromtimestamp(event['timestamp'] / 1000))}: {event['message']}")

    return events['nextForwardToken']


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
def status(ctx, verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the latest task

    Logs are not created until a task is in the RUNNING state,
    so the logs returned by this command might be out of date
    """
    ctx.ensure_object(dict)
    node = ctx.obj['node']
    monitor(node, load_or_init_nodes(node), verbose, num_lines, log_type, follow_tail)
