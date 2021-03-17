import json

import numerapi

from cli.src.constants import *
from cli.src.misc import copy_example
from cli.src.util.docker import terraform
from cli.src.util.files import \
    load_or_init_nodes,\
    store_config
from cli.src.util.keys import \
    get_provider_keys,\
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
         f"Defaults to {DEFAULT_SIZE} (run 'numerai config size-presets' to see options)."
         f"\nSee https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for more info")
@click.option(
    '--path', '-p', type=str,
    help=f"Target a file path. Defaults to current directory ({DEFAULT_PATH}).")
@click.option(
    '--example', '-e', type=str,
    help=f'Specify an example to use for this node. Options are {EXAMPLES}.')
@click.pass_context
def create(ctx, verbose, provider, size, path, example):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    model_id = model['id']

    if example:
        click.secho(f'copying {example} example to {path}...')
        copy_example(ctx, example, path, verbose)

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
    if provider:
        nodes_config[node]['provider'] = provider
    if size:
        nodes_config[node]['cpu'] = SIZE_PRESETS[size][0]
        nodes_config[node]['memory'] = SIZE_PRESETS[size][1]
    if path:
        nodes_config[node]['path'] = os.path.abspath(path)
    if model_id:
        nodes_config[node]['model_id'] = model_id
    store_config(NODES_PATH, nodes_config)

    # terraform apply
    provider_keys = get_provider_keys(node)
    print(provider_keys)
    click.secho(f'running terraform to provision cloud infrastructure...')
    terraform(f'apply -auto-approve', verbose,
              env_vars=provider_keys,
              inputs={'node_config_file': 'nodes.json'})
    click.secho('successfully created cloud resources!', fg='green')

    # terraform output for AWS nodes
    click.echo(f'saving node configuration to {NODES_PATH}...')
    res = terraform(f"output -json aws_nodes", verbose).stdout.decode('utf-8')
    aws_nodes = json.loads(res)
    for node, data in aws_nodes.items():
        nodes_config[node].update(data)
    store_config(NODES_PATH, nodes_config)
    if verbose:
        click.secho(f'new config:\n{str(load_or_init_nodes())}')

    if model_id:
        napi = numerapi.NumerAPI(*get_numerai_keys())
        webhook_url = nodes_config[node]['webhook_url']
        click.echo(f'registering webhook {webhook_url} for model {model_id}...')
        napi.raw_query(
            '''
            mutation (
                $modelId: String!
                $newSubmissionWebhook: String!
            ) {
                setSubmissionWebhook(
                    modelId: $modelId
                    newSubmissionWebhook: $newSubmissionWebhook
                )
            }
            ''',
            variables={
                'modelId': model_id,
                'newSubmissionWebhook': webhook_url
            },
            authorization=True
        )
    click.secho('Prediction Node created successfully', fg='green')