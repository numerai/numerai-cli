"""Config command for Numerai CLI"""

import os

from numerapi import base_api
from numerai.cli.constants import (
    DEFAULT_PROVIDER,
    DEFAULT_SIZE_GCP,
    PROVIDER_AWS,
    PROVIDER_AZURE,
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
from numerai.cli.util import docker
from numerai.cli.util.files import (
    load_or_init_nodes,
    store_config,
    copy_example,
    copy_file,
)
from numerai.cli.util.keys import get_provider_keys, get_numerai_keys
from numerai.cli.util.terraform import (
    apply_terraform,
    create_azure_registry,
    create_gcp_registry,
)

import click


@click.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--provider",
    "-P",
    type=str,
    help=f"Select a cloud provider. One of {PROVIDERS}. "
    f"Defaults to {DEFAULT_PROVIDER}.",
)
@click.option(
    "--size",
    "-s",
    type=str,
    help=f"CPU credits (cores * 1024) and Memory (in MiB) used in the deployed container. "
    f"Defaults to {DEFAULT_SIZE} (run `numerai list-constants` to see options).",
)
@click.option(
    "--cpu",
    type=str,
    help=f"For AWS only, CPUs to allocate to your node"
    f"Defaults to 2 (run `numerai list-constants` to see options).",
)
@click.option(
    "--memory",
    type=str,
    help=f"For AWS only, memory in GB to allocate to your node"
    f"Defaults to 16 (run `numerai list-constants` to see options).",
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
def config(
    ctx,
    verbose,
    provider,
    size,
    cpu,
    memory,
    path,
    example,
    cron,
    timeout_minutes,
    register_webhook,
):
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
        {
            key: default
            for key, default in DEFAULT_SETTINGS.items()
            if key not in nodes_config[node]
        }
    )
    # update node as needed
    node_conf = nodes_config[node]

    if timeout_minutes:
        node_conf["timeout_minutes"] = timeout_minutes

    if provider:
        node_conf["provider"] = provider
    else:
        provider = node_conf["provider"]

    if timeout_minutes and provider == PROVIDER_AZURE:
        click.secho(
            "Timeout settings are unavailable for Azure and this input will be ignored.",
            fg="yellow",
        )
    elif timeout_minutes:
        node_conf["timeout_minutes"] = timeout_minutes

    if provider == PROVIDER_GCP and size is not None and "mem-" in size:
        click.secho(
            "Invalid size: mem sizes are invalid for GCP due to sizing constraints with Google Cloud Run.",
            fg="red",
        )
        click.secho(
            "Visit https://cloud.google.com/run/docs/configuring/services/memory-limits to learn more.",
            fg="red",
        )
        exit(1)

    if size and (cpu or memory):
        click.secho(
            "Cannot provide size and CPU or Memory. Either use size or provide CPU and Memory.",
            fg="red",
        )
        exit(1)
    if (cpu or memory) and node_conf["provider"] != PROVIDER_AWS:
        click.secho(
            "Specifying CPU and Memory is only valid for AWS nodes. (run `numerai list-constants` to see options).",
            fg="red",
        )
        exit(1)
    elif (cpu or memory) and (
        not (cpu or node_conf["cpu"]) or not (memory or node_conf["memory"])
    ):
        click.secho(
            "One of CPU and Memory is missing either from your options or from your node configuration."
            "Provide both CPU and Memory to configure node size, or use size."
            "(run `numerai list-constants` to see options).",
            fg="red",
        )
        exit(1)
    elif cpu or memory:
        if cpu:
            node_conf["cpu"] = int(cpu) * 1024
        if memory:
            node_conf["memory"] = int(memory) * 1024
    elif size:
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
    docker.check_for_dockerfile(nodes_config[node]["path"])
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
        provider_registry_conf = create_azure_registry(
            provider, provider_keys, verbose=verbose
        )
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
        node_conf["artifact_registry_login_url"] = (
            f"https://{registry_parts[3]}-docker.pkg.dev/"
        )
        node_conf["docker_repo"] = (
            f"{registry_parts[3]}-docker.pkg.dev/{registry_parts[1]}/numerai-container-registry/{node}:latest"
        )
        docker.login(node_conf, verbose)
        try:
            docker.manifest_inspect(node_conf["docker_repo"], verbose)
        except Exception as e:
            docker.pull("hello-world:linux", verbose)
            docker.tag("hello-world:linux", node_conf["docker_repo"], verbose)
            docker.push(node_conf["docker_repo"], verbose)
        nodes_config[node] = node_conf

    store_config(NODES_PATH, nodes_config)

    apply_terraform(nodes_config, affected_providers, provider, verbose)

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
