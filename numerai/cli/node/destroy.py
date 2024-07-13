"""Destroy command for Numerai CLI"""

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform
from numerai.cli.util.files import load_or_init_nodes, store_config, copy_file
from numerai.cli.util.keys import get_provider_keys, get_numerai_keys


@click.command()
@click.option("--preserve-node-config", "-p", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def destroy(ctx, preserve_node_config, verbose):
    """
    Uses Terraform to destroy a Numerai Compute cluster.
    This will delete everything, including:
        - lambda url
        - docker container and associated task
        - all logs
    This command is idempotent and safe to run multiple times.
    """

    ctx.ensure_object(dict)
    model = ctx.obj["model"]
    node = model["name"]
    if not os.path.exists(CONFIG_PATH):
        click.secho(".numerai directory not setup, run `numerai setup`...", fg="red")
        return

    try:
        nodes_config = load_or_init_nodes()
        node_config = nodes_config[node]
        provider_keys = get_provider_keys(node)
        provider = node_config["provider"]
    except (KeyError, FileNotFoundError) as e:
        click.secho(
            f"make sure you run `numerai setup` and "
            f"`numerai node -n {node} config` first...",
            fg="red",
        )
        return

    if not preserve_node_config:
        click.secho("backing up nodes.json...")
        copy_file(NODES_PATH, f"{NODES_PATH}.backup", force=True, verbose=True)

    try:
        click.secho(
            f"deleting node configuration"
            + (" (temporarily)" if preserve_node_config else "")
            + "..."
        )
        del nodes_config[node]
        store_config(NODES_PATH, nodes_config)

        click.secho("deleting cloud resources for node...")
        terraform(
            "apply -auto-approve",
            verbose,
            provider,
            env_vars=provider_keys,
            inputs={"node_config_file": "nodes.json"},
        )

    except Exception as e:
        click.secho(e.__str__(), fg="red")
        nodes_config[node] = node_config
        store_config(NODES_PATH, nodes_config)
        return

    if "model_id" in node_config and "webhook_url" in node_config:
        napi = base_api.Api(*get_numerai_keys())
        model_id = node_config["model_id"]
        webhook_url = node_config["webhook_url"]
        click.echo(f"deregistering webhook {webhook_url} for model {model_id}...")
        napi.set_submission_webhook(model_id, None)

    click.secho("Prediction Node destroyed successfully", fg="green")

    if preserve_node_config:
        click.secho("re-adding node config to nodes.json...", fg="green")
        nodes_config[node] = node_config
        store_config(NODES_PATH, nodes_config)
