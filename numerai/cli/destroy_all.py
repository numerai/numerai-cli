"""Destroy command for Numerai CLI"""

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform
from numerai.cli.util.files import load_or_init_nodes, store_config, copy_file
from numerai.cli.util.keys import get_provider_keys, get_numerai_keys


@click.command("destroy-all", help="Destroy all nodes")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--preserve-node-config", "-p", is_flag=True)
@click.pass_context
def destroy_all(ctx, verbose, preserve_node_config):
    """
    Uses Terraform to destroy a Numerai Compute clusters for both Tournament and Signals.
    This will delete everything, including:
        - lambda url
        - docker container and associated task
        - all logs
    This command is idempotent and safe to run multiple times.
    """
    if not os.path.exists(CONFIG_PATH):
        click.secho(".numerai directory not setup, run `numerai setup`...", fg="red")
        return

    if not click.prompt(
        "THIS WILL DELETE ALL YOUR NODES, ARE YOU SURE? (y/n)",
    ):
        exit(0)

    nodes_config = load_or_init_nodes()

    if len(nodes_config) == 0:
        click.secho("No nodes to destroy", fg="green")
        return

    try:
        provider_keys = {
            nodes_config[node]["provider"]: get_provider_keys(node)
            for node in nodes_config
        }
    except (KeyError, FileNotFoundError) as e:
        click.secho(
            f"make sure you run `numerai setup` and " f"`numerai node config` first...",
            fg="red",
        )
        return

    click.secho("backing up nodes.json and deleting current config...")
    copy_file(NODES_PATH, f"{NODES_PATH}.backup", force=True, verbose=True)
    store_config(NODES_PATH, {})

    try:
        click.secho(f"destroying nodes...")
        for provider, provider_keys in provider_keys.items():
            click.secho(f"deleting cloud resources for {provider}...")
            terraform(
                "destroy -auto-approve",
                verbose,
                provider,
                env_vars=provider_keys,
                inputs={"node_config_file": "nodes.json"},
            )

    except Exception as e:
        click.secho(e.__str__(), fg="red")
        click.secho("restoring nodes.json...", fg="green")
        store_config(NODES_PATH, nodes_config)
        return

    napi = base_api.Api(*get_numerai_keys())
    for node, node_config in nodes_config.items():
        if "model_id" in node_config and "webhook_url" in node_config:
            model_id = node_config["model_id"]
            webhook_url = node_config["webhook_url"]
            click.echo(f"deregistering webhook {webhook_url} for model {model_id}...")
            napi.set_submission_webhook(model_id, None)

    click.secho("Prediction Nodes destroyed successfully", fg="green")

    if preserve_node_config:
        click.secho("restoring nodes.json...", fg="green")
        store_config(NODES_PATH, nodes_config)
