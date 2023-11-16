"""Destroy command for Numerai CLI"""
import click
from numerapi import base_api

from numerai.cli.node import get_models
from numerai.cli.constants import *
from numerai.cli.node.destroy import destroy_node
from numerai.cli.util.files import load_or_init_nodes


@click.command("destroy-all", help="Destroy all nodes")
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def destroy_all(ctx, verbose):
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
    models = get_models(TOURNAMENT_NUMERAI)

    for _, model in models.items():
        node = model["name"]
        if node in nodes_config:
            destroy_node(node, verbose)
