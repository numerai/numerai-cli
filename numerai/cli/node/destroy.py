import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform
from numerai.cli.util.files import \
    load_or_init_nodes, \
    store_config, \
    copy_file
from numerai.cli.util.keys import get_provider_keys, get_numerai_keys
from numerai.cli.node.config import load_or_init_registry_config

@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def destroy(ctx, verbose):
    """
    Uses Terraform to destroy Numerai Compute cluster in AWS.
    This will delete everything, including:
        - lambda url
        - docker container and associated task
        - all logs
    This command is idempotent and safe to run multiple times.
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    if not os.path.exists(CONFIG_PATH):
        click.secho(f".numerai directory not setup, run `numerai setup`...", fg='red')
        return

    try:
        nodes_config = load_or_init_nodes()
        node_config = nodes_config[node]
        provider_keys = get_provider_keys(node)
        provider = node_config['provider']
    except (KeyError, FileNotFoundError) as e:
        click.secho(f"make sure you run `numerai setup` and "
                    f"`numerai node -n {node} config` first...", fg='red')
        return

    try:
        click.secho(f"deleting node configuration...")
        del nodes_config[node]
        store_config(NODES_PATH, nodes_config)
        copy_file(NODES_PATH,f'{CONFIG_PATH}/{provider}/',force=True,verbose=True)
        
        click.secho(f"deleting cloud resources for node...")
        terraform(f'apply -auto-approve', verbose, provider,
                  env_vars=provider_keys,
                  inputs={'node_config_file': 'nodes.json'})

    except Exception as e:
        click.secho(e.__str__(), fg='red')
        nodes_config[node] = node_config
        store_config(NODES_PATH, nodes_config)
        return

    if 'model_id' in node_config and 'webhook_url' in node_config:
        napi = base_api.Api(*get_numerai_keys())
        model_id = node_config['model_id']
        webhook_url = node_config['webhook_url']
        click.echo(f'deregistering webhook {webhook_url} for model {model_id}...')
        napi.set_submission_webhook(model_id, None)

    click.secho("Prediction Node destroyed successfully", fg='green')
    
    if provider == 'azure':
        remaining_azure_nodes=sum(1 for node in nodes_config.values() if node['provider'] == 'azure')
        if remaining_azure_nodes==0:
            click.secho(f"Provider: '{provider}' has no more nodes, destroying Container Registry...", fg='yellow')
            #provider_registry_conf=load_or_init_registry_config(provider,verbose)
            # Load and delete registry config
            all_registry_conf=load_or_init_registry_config()
            del nodes_config[provider]
            store_config(REGISTRY_PATH, all_registry_conf)
            
            # Terrafom destroy azure container registry
            terraform(f'-chdir=container_registry/azure destroy -auto-approve ', verbose, provider,
            env_vars=provider_keys)
            click.secho(f"Provider: '{provider}' Container Registry destroyed", fg='green')
        else:
            click.secho(f"Provider: '{provider}' still has node, not destroying its Container Registry", fg='green')
