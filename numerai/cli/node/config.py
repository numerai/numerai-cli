import json

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform, check_for_dockerfile
from numerai.cli.util.files import \
    load_or_init_nodes, \
    store_config, \
    copy_example
from numerai.cli.util.keys import \
    get_provider_keys, \
    get_numerai_keys


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--provider', '-P', type=str,
    help=f"Select a cloud provider. One of {PROVIDERS}. "
         f"Defaults to {DEFAULT_PROVIDER}.")
@click.option(
    '--size', '-s', type=str,
    help=f"CPU credits (cores * 1024) and Memory (in MiB) used in the deployed container. "
         f"Defaults to {DEFAULT_SIZE} (run `numerai list-constants` to see options).")
@click.option(
    '--path', '-p', type=str,
    help=f"Target a file path. Defaults to current directory ({DEFAULT_PATH}).")
@click.option(
    '--example', '-e', type=click.Choice(EXAMPLES),
    help=f'Specify an example to use for this node. Options are {EXAMPLES}.')
@click.option(
    '--cron', '-c', type=str,
    help=f'A cron expression to trigger this node on a schedule '
         f'(e.g. "30 18 ? * 7 *" to execute at 18:30 UTC every Saturday). '
         f'This prevents your webhook from auto-registering. '
         f'Check the AWS docs for more info about cron expressions: '
         f'https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html')
@click.option(
    '--register-webhook', '-r', is_flag=True,
    help=f'Forces your webhook to register with Numerai. '
         f'Use in conjunction with options that prevent webhook auto-registering.')
@click.pass_context
def config(ctx, verbose, provider, size, path, example, cron, register_webhook):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    model_id = model['id']

    if example is not None:
        path = copy_example(example, path, verbose)

    # get nodes config object and set defaults for this node
    click.secho(f'configuring node "{node}"...')
    nodes_config = load_or_init_nodes()
    nodes_config.setdefault(node, {})
    nodes_config[node].update({
        key: default
        for key, default in DEFAULT_SETTINGS.items()
        if key not in nodes_config[node]
    })
    # update node as needed
    node_conf = nodes_config[node]
    if provider:
        node_conf['provider'] = provider
    if size:
        node_conf['cpu'] = SIZE_PRESETS[size][0]
        node_conf['memory'] = SIZE_PRESETS[size][1]
    if path:
        node_conf['path'] = os.path.abspath(path)
    if model_id:
        node_conf['model_id'] = model_id
    if cron:
        node_conf['cron'] = cron
    nodes_config[node] = node_conf

    # double check there is a dockerfile in the path we are about to configure
    check_for_dockerfile(nodes_config[node]['path'])
    store_config(NODES_PATH, nodes_config)

    # terraform apply
    provider_keys = get_provider_keys(node)
    click.secho(f'running terraform to provision cloud infrastructure...')
    # TODO: check if keys necessary for Azure can be loaded successfully
    terraform(f'apply -auto-approve', verbose,
              env_vars=provider_keys,
              inputs={'node_config_file': 'nodes.json'})
    click.secho('cloud resources created successfully', fg='green')

    # terraform output for AWS nodes
    click.echo(f'saving node configuration to {NODES_PATH}...')
    res = terraform(f"output -json aws_nodes", verbose).decode('utf-8')
    try:
        aws_nodes = json.loads(res)
    except json.JSONDecodeError:
        click.secho("failed to save node configuration, pleas retry.", fg='red')
        return
    for node_name, data in aws_nodes.items():
        nodes_config[node_name].update(data)
    store_config(NODES_PATH, nodes_config)
    if verbose:
        click.secho(f'new config:\n{json.dumps(load_or_init_nodes(), indent=2)}')

    webhook_url = nodes_config[node]['webhook_url']
    napi = base_api.Api(*get_numerai_keys())
    if not cron or register_webhook:
        click.echo(f'registering webhook {webhook_url} for model {model_id}...')
        napi.set_submission_webhook(model_id, webhook_url)

    else:
        click.echo(f'removing registered webhook for model {model_id}...')
        napi.set_submission_webhook(model_id, None)

    click.secho('Prediction Node configured successfully. '
                'Next: deploy and test your node', fg='green')