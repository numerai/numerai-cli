import json

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform, check_for_dockerfile
          
# For Azure use                      
from numerai.cli.util import docker    

from numerai.cli.util.files import \
    load_or_init_nodes, \
    store_config, \
    copy_example, \
    copy_file, \
    maybe_create, \
    load_config
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
         f'(e.g. "30 18 ? * 7 *" to execute at 18:30 UTC every Saturday. '
         f'"0 30 13 * * SUN,TUE,WED,THU,FRI" to execute at 13:30 UTC every Sunday, Tuesday, Wednesday, Thursday and Friday). '
         f'This prevents your webhook from auto-registering. '
         f'Check the AWS docs for more info about cron expressions: '
         f'https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html'
         f'Check the Azure docs for more info about cron expressions: '
         f'https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=python-v2%2Cin-process&pivots=programming-language-python#ncrontab-expressions')
@click.option(
    '--register-webhook', '-r', is_flag=True,
    help=f'Forces your webhook to register with Numerai. '
         f'Use in conjunction with options that prevent webhook auto-registering.')
@click.pass_context
def config(ctx, verbose, provider, size, path, example, cron, register_webhook):
    """
    Uses Terraform to create a full Numerai Compute cluster in your desired provider.
    Prompts for your cloud provider and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    model_id = model['id']
    
    click.secho(f'Input provider "{provider}"...')
    click.secho(f'Input size "{size}"...')
    click.secho(f'Input node name "{node}"...')
    
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
    #click.secho(f'Provider: "{provider}"...')    
    click.secho(f'Current node config: "{node_conf}"...')
    if provider:
        node_conf['provider'] = provider
    else:
        provider = node_conf['provider']
        
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
    
    # Added after tf directory restructure: copy nodes.json to providers' tf directory
    copy_file(NODES_PATH,f'{CONFIG_PATH}/{provider}/',force=True,verbose=True)


    # terraform apply: create cloud resources
    provider_keys = get_provider_keys(node)
    click.secho(f'running terraform to provision cloud infrastructure...')
    
    # Azure only: Need to create a master Azure Container Registry and push a dummy placeholder image, before deploying the rest of the resources
    if provider == 'azure':
        provider_registry_conf=load_or_init_registry_config(provider,verbose)
        
        # TODO: Add checks to see if registry config is valid, if not valid, create and replace with new registry config
        # click.secho(f'Current registry config: {provider_registry_conf}, creating a new registry', fg='green')
        # Create Azure Container Registry if it doesn't exist
        if provider_registry_conf == {}:
            click.secho(f'No container registry for provider: {provider}, creating a new registry', fg='yellow')
            provider_registry_conf = create_azure_registry(provider, provider_keys, verbose=False)
        
        #click.secho(f'Appending provider_registry_conf:{provider_registry_conf}, to node_conf', fg='yellow')
        node_conf.update(provider_registry_conf)
        # Create a placeholder image and push it to the registry
        node_conf['docker_repo'] = f'{node_conf["acr_login_server"]}/{node}'
               
        docker.login(node_conf,verbose)
        docker.pull('hello-world:linux', verbose)
        
        docker.tag('hello-world:linux',node_conf['docker_repo'], verbose)
        docker.push(node_conf['docker_repo'], verbose)
        #click.secho(f'node_config is: {node_conf}, saved once again', fg='yellow')
        
        nodes_config[node] = node_conf
        store_config(NODES_PATH, nodes_config)    
        copy_file(NODES_PATH,f'{CONFIG_PATH}/{provider}/',force=True,verbose=True)

    if provider == 'aws' or provider == 'azure':
        terraform(f'apply -auto-approve', verbose, provider,
            env_vars=provider_keys,
            inputs={'node_config_file': 'nodes.json'})
    else:
        click.secho(f'provider {provider} not supported', fg='red')
        exit(1)
    click.secho('cloud resources created successfully', fg='green') 

    # terraform output for node config, same for aws and azure
    click.echo(f'saving node configuration to {NODES_PATH}...')
    
    res = terraform(f"output -json {provider}_nodes", verbose, provider).decode('utf-8')
    try:
        nodes = json.loads(res)
    except json.JSONDecodeError:
        click.secho("failed to save node configuration, please retry.", fg='red')
        return
    for node_name, data in nodes.items():
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
    
    
def load_or_init_registry_config(provider=None, verbose=False):
    """Load or initialize the registry config file, 
    The registry config file stores the container registry 
    details for each provider

    Args:
        provider (str, optional): Specify the provider's registry_config to load. Defaults to None, which loads all registry configs.
        verbose (bool, optional): Verbose flag. Defaults to False. 

    Returns:
        dict: All providers / specific provider's registry config 
    """
    maybe_create(REGISTRY_PATH)
    cfg = load_config(REGISTRY_PATH)
    try:
        if provider==None:
            return cfg
        elif provider == 'azure':
            # Return the specific registry if it exists
            return cfg[provider] 
        else:
            click.secho(f"Unsupported provider: '{cfg[provider]}'", fg='red')
            exit(1)
    except KeyError:
        click.secho(f"Return an empty container registry for provider: {provider}", fg='yellow')
        cfg[provider]={}
        store_config(REGISTRY_PATH, cfg)
        return cfg[provider]

# TODO: add support for other container registry, to be configured by -registry setting?
def create_azure_registry(provider, provider_keys, registry=None, verbose=False):
    terraform(f"-chdir=container_registry/azure init -upgrade", verbose, provider)
    terraform(f'-chdir=container_registry/azure apply -auto-approve ', verbose, provider,
                env_vars=provider_keys)
    res = terraform(f'-chdir=container_registry/azure output -json acr_repo_details', verbose, provider).decode('utf-8')
    provider_registry_conf=json.loads(res)
    
    click.secho(f'Created new provider_registry_conf:{provider_registry_conf}, updating {REGISTRY_PATH}', fg='yellow')
    all_registry_conf=load_or_init_registry_config()
    all_registry_conf[provider]=provider_registry_conf
    store_config(REGISTRY_PATH, all_registry_conf)
    return provider_registry_conf
            