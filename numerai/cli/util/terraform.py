import json

from numerai.cli.constants import PROVIDERS, NODES_PATH
from numerai.cli.util.docker import terraform
from numerai.cli.util import docker
from numerai.cli.util.files import load_or_init_nodes, store_config
from numerai.cli.util.keys import load_or_init_keys

import click


def apply_terraform(nodes_config, affected_providers, provider, verbose):
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
    res = terraform("output -json artifact_registry_details", True, provider).decode(
        "utf-8"
    )
    return json.loads(res)
