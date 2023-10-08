"""Config command for Numerai CLI"""
import json
import os
import click
from numerapi import base_api
from numerai.cli.constants import (
    DEFAULT_PROVIDER,
    DEFAULT_SIZE_GCP,
    PROVIDERS,
    DEFAULT_SIZE,
    EXAMPLES,
    DEFAULT_SETTINGS,
    DEFAULT_PATH,
    SIZE_PRESETS,
    NODES_PATH,
    CONFIG_PATH,
    PROVIDER_GCP,
)
from numerai.cli.util.docker import terraform, check_for_dockerfile
from numerai.cli.util import docker
from numerai.cli.util.files import (
    load_or_init_nodes,
    store_config,
    copy_example,
    copy_file,
)
from numerai.cli.util.keys import get_provider_keys, get_numerai_keys, load_or_init_keys


@click.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--provider",
    "-P",
    type=str,
    help=f"Select a cloud provider. One of {PROVIDERS}. " f"Defaults to {DEFAULT_PROVIDER}.",
)
@click.option(
    "--size",
    "-s",
    type=str,
    help=f"CPU credits (cores * 1024) and Memory (in MiB) used in the deployed container. "
    f"Defaults to {DEFAULT_SIZE} (run `numerai list-constants` to see options).",
)
@click.option(
    "--path",
    "-p",
    type=str,
    help=f"Target a file path. Defaults to current directory ({DEFAULT_PATH}).",
)
@click.option(
    "--example",
    "-e",
    type=click.Choice(EXAMPLES),
    help=f"Specify an example to use for this node. Options are {EXAMPLES}.",
)
@click.option(
    "--cron",
    "-c",
    type=str,
    help="A cron expression to trigger this node on a schedule "
    '(e.g. "30 18 ? * 7 *" to execute at 18:30 UTC every Saturday. '
    '"0 30 13 * * SUN,TUE,WED,THU,FRI" to execute at 13:30 UTC every Sunday, Tuesday, Wednesday, Thursday and Friday). '
    "This prevents your webhook from auto-registering. "
    "Check the AWS docs for more info about cron expressions: "
    "https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html"
    "Check the Azure docs for more info about cron expressions: "
    "https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=python-v2%2Cin-process&pivots=programming-language-python#ncrontab-expressions",
)
@click.option(
    "--timeout-minutes",
    type=str,
    help="Maximum time to allow this node to run when triggered. Defaults to 60 minutes. Valid for GCP only.",
)
@click.option(
    "--register-webhook",
    "-r",
    is_flag=True,
    help="Forces your webhook to register with Numerai. "
    "Use in conjunction with options that prevent webhook auto-registering.",
)
@click.pass_context
def config(ctx, verbose, provider, size, path, example, cron, timeout_minutes, register_webhook):
    """
    Uses Terraform to create a full Numerai Compute cluster in your desired provider.
    Prompts for your cloud provider and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """
    ctx.ensure_object(dict)
    model = ctx.obj["model"]
    node = model["name"]
    model_id = model["id"]

    click.secho(f'Input provider "{provider}"...')
    click.secho(f'Input size "{size}"...')
    click.secho(f'Input node name "{node}"...')

    if example is not None:
        path = copy_example(example, path, verbose)

    # get nodes config object and set defaults for this node
    click.secho(f'configuring node "{node}"...')
    nodes_config = load_or_init_nodes()
    nodes_config.setdefault(node, {})

    using_defaults = False
    if nodes_config[node] is None or nodes_config[node] == {}:
        using_defaults = True

    # Find any providers that will be affected by this config update
    affected_providers = [provider]

    if nodes_config[node] is not None and "provider" in nodes_config[node]:
        affected_providers.append(nodes_config[node]["provider"])
    elif provider is None:
        affected_providers.append(DEFAULT_SETTINGS["provider"])
    affected_providers = set(filter(None, affected_providers))

    nodes_config[node].update(
        {key: default for key, default in DEFAULT_SETTINGS.items() if key not in nodes_config[node]}
    )
    # update node as needed
    node_conf = nodes_config[node]

    if timeout_minutes:
        node_conf["timeout_minutes"] = timeout_minutes

    if provider:
        node_conf["provider"] = provider
    else:
        provider = node_conf["provider"]

    if provider == PROVIDER_GCP and size is not None and "mem-" in size:
        click.secho(
            "Invalid size: mem sizes are invalid for GCP due to sizing constraints with Google Cloud Run.", fg="red"
        )
        click.secho(
            "Visit https://cloud.google.com/run/docs/configuring/services/memory-limits to learn more.", fg="red"
        )
        exit(1)

    if size:
        node_conf["cpu"] = SIZE_PRESETS[size][0]
        node_conf["memory"] = SIZE_PRESETS[size][1]
    elif node_conf["provider"] == PROVIDER_GCP and using_defaults:
        node_conf["cpu"] = SIZE_PRESETS[DEFAULT_SIZE_GCP][0]
        node_conf["memory"] = SIZE_PRESETS[DEFAULT_SIZE_GCP][1]

    if path:
        node_conf["path"] = os.path.abspath(path)
    if model_id:
        node_conf["model_id"] = model_id
    if cron:
        node_conf["cron"] = cron
    nodes_config[node] = node_conf

    click.secho(f'Current node config: "{node_conf}"...')

    # double check there is a dockerfile in the path we are about to configure
    check_for_dockerfile(nodes_config[node]["path"])
    store_config(NODES_PATH, nodes_config)

    # Added after tf directory restructure: copy nodes.json to providers' tf directory
    for affected_provider in affected_providers:
        copy_file(
            NODES_PATH,
            f"{CONFIG_PATH}/{affected_provider}/",
            force=True,
            verbose=verbose,
        )

    # terraform apply: create cloud resources
    provider_keys = get_provider_keys(node)
    click.secho("Running terraform to provision cloud infrastructure...")

    # Azure only: Need to create a master Azure Container Registry and push a dummy placeholder image, before deploying the rest of the resources
    if provider == "azure":
        provider_registry_conf = create_azure_registry(provider, provider_keys, verbose=verbose)
        node_conf.update(provider_registry_conf)
        node_conf["docker_repo"] = f'{node_conf["acr_login_server"]}/{node}'
        docker.login(node_conf, verbose)
        try:
            docker.manifest_inspect(node_conf["docker_repo"], verbose)
        except Exception as e:
            print(e)
            docker.pull("hello-world:linux", verbose)
            docker.tag("hello-world:linux", node_conf["docker_repo"], verbose)
            docker.push(node_conf["docker_repo"], verbose)
        nodes_config[node] = node_conf
    elif provider == "gcp":
        provider_registry_conf = create_gcp_registry(provider, verbose=verbose)
        node_conf.update(provider_registry_conf)
        registry_parts = node_conf["registry_id"].split("/")
        node_conf["artifact_registry_login_url"] = f'https://{registry_parts[3]}-docker.pkg.dev/'
        node_conf[
            "docker_repo"
        ] = f'{registry_parts[3]}-docker.pkg.dev/{registry_parts[1]}/numerai-container-registry/{node}:latest'
        docker.login(node_conf, verbose)
        try:
            docker.manifest_inspect(node_conf["docker_repo"], verbose)
        except Exception as e:
            docker.pull("hello-world:linux", verbose)
            docker.tag("hello-world:linux", node_conf["docker_repo"], verbose)
            docker.push(node_conf["docker_repo"], verbose)
        nodes_config[node] = node_conf

    store_config(NODES_PATH, nodes_config)

    # Apply terraform for any affected provider
    for affected_provider in affected_providers:
        if affected_provider in PROVIDERS:
            click.secho(f"Updating resources in {affected_provider}")
            terraform(
                "apply -auto-approve",
                verbose,
                affected_provider,
                env_vars=load_or_init_keys(affected_provider),
                inputs={"node_config_file": "nodes.json"},
            )
        else:
            click.secho(f"provider {affected_provider} not supported", fg="red")
            exit(1)
    click.secho("cloud resources created successfully", fg="green")

    # terraform output for node config, same for aws and azure
    click.echo(f"saving node configuration to {NODES_PATH}...")

    res = terraform(f"output -json {provider}_nodes", verbose, provider).decode("utf-8")
    try:
        nodes = json.loads(res)
    except json.JSONDecodeError:
        click.secho("failed to save node configuration, please retry.", fg="red")
        return
    for node_name, data in nodes.items():
        nodes_config[node_name].update(data)

    store_config(NODES_PATH, nodes_config)
    if verbose:
        click.secho(f"new config:\n{json.dumps(load_or_init_nodes(), indent=2)}")

    webhook_url = nodes_config[node]["webhook_url"]
    napi = base_api.Api(*get_numerai_keys())
    if not cron or register_webhook:
        click.echo(f"registering webhook {webhook_url} for model {model_id}...")
        napi.set_submission_webhook(model_id, webhook_url)

    else:
        click.echo(f"removing registered webhook for model {model_id}...")
        napi.set_submission_webhook(model_id, None)

    click.secho(
        "Prediction Node configured successfully. " "Next: deploy and test your node",
        fg="green",
    )


def create_azure_registry(provider, provider_keys, verbose):
    """Creates a registry for azure"""
    terraform("init -upgrade", verbose, provider)
    terraform(
        'apply -target="azurerm_container_registry.registry[0]" -target="azurerm_resource_group.acr_rg[0]" -auto-approve ',
        verbose,
        "azure",
        env_vars=provider_keys,
        inputs={"node_config_file": "nodes.json"},
    )
    res = terraform("output -json acr_repo_details", True, provider).decode("utf-8")
    return json.loads(res)


def create_gcp_registry(provider, verbose):
    """Creates a registry for GCP"""
    terraform("init -upgrade", verbose, provider)
    terraform(
        'apply -target="google_project_service.cloud_resource_manager" -auto-approve ',
        verbose,
        "gcp",
        inputs={"node_config_file": "nodes.json"},
    )
    terraform(
        'apply -target="google_artifact_registry_repository.registry[0]" -auto-approve ',
        verbose,
        "gcp",
        inputs={"node_config_file": "nodes.json"},
    )
    res = terraform("output -json artifact_registry_details", True, provider).decode("utf-8")
    return json.loads(res)
