from numerai.cli.constants import *
from numerai.cli.util import files
from numerai.cli.util.terraform import apply_terraform

import click


@click.command()
@click.option(
    "--example",
    "-e",
    type=click.Choice(EXAMPLES),
    default=DEFAULT_EXAMPLE,
    help=f"Specify the example to copy, defaults to {DEFAULT_EXAMPLE}. "
    f"Options are {EXAMPLES}.",
)
@click.option(
    "--dest",
    "-d",
    type=str,
    help=f"Destination folder to which example code is written. "
    f"Defaults to the name of the example.",
)
@click.option("--verbose", "-v", is_flag=True)
def copy_example(example, dest, verbose):
    """
    Copies all example files into the current directory.

    WARNING: this will overwrite the following files if they exist:

        - Python: Dockerfile, model.py, train.py, predict.py, and requirements.txt

        - RLang:  Dockerfile, install_packages.R, main.R
    """
    files.copy_example(example, dest, verbose)


@click.command()
def list_constants():
    """
    Display default and constant values used by the CLI.

    Does NOT show currently configured node values.
    """
    click.secho(CONSTANTS_STR, fg="green")
    click.secho("SIZE_PRESETS:", fg="green")
    for size, preset in SIZE_PRESETS.items():
        suffix = "(default)" if size == DEFAULT_SIZE else ""
        suffix = "(default - gcp)" if size == DEFAULT_SIZE_GCP else suffix
        click.secho(
            f"  {size} -> cpus: {preset[0] / 1024}, "
            f"mem: {preset[1] / 1024} GB {suffix}",
            fg=(
                "green"
                if size == DEFAULT_SIZE or size == DEFAULT_SIZE_GCP
                else "yellow"
            ),
        )
    click.secho(
        "Due to GCP Cloud Run size constraints, 'mem' sizes are not allowed when using GCP."
    )
    click.secho(
        "For AWS, use one of these sizes, or specify your own CPU and Memory in cores and GB using --cpu and --memory options.\n"
        "See https://learn.microsoft.com/en-us/azure/container-apps/containers#configuration for Azure,\n"
        "or https://cloud.google.com/run/docs/configuring/services/memory-limits for GCP \n"
        "to learn more info about allowed size presets for those providers."
    )


@click.command()
@click.option(
    "--size",
    "-s",
    type=int,
    required=True,
    help="Specify the volume size in GB you'd like your AWS nodes to share.",
)
@click.option("--verbose", "-v", is_flag=True)
def add_volume_aws(size, verbose):
    """
    Set the volume size for AWS nodes. This volume is shared by all nodes.
    """
    click.secho("Setting volume size for AWS nodes...", fg="yellow")
    # get nodes config object
    nodes_config = files.load_or_init_nodes()
    print(nodes_config)
    # set volume size for all nodes to same size
    for node in nodes_config:
        nodes_config[node]["volume"] = size
    files.store_config(NODES_PATH, nodes_config)
    files.copy_file(
        NODES_PATH,
        f"{CONFIG_PATH}/{PROVIDER_AWS}/",
        force=True,
        verbose=verbose,
    )
    click.secho(f"Applying terraform to add {size} GB volume...", fg="yellow")
    apply_terraform(nodes_config, [PROVIDER_AWS], PROVIDER_AWS, verbose=verbose)
    click.secho("Volume size updated successfully!", fg="green")
