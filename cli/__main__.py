import click
from colorama import init

from cli import configure, create, destroy, compute, docker


@click.group()
def cli():
    """This script allows you to setup Numer.ai compute node and deploy docker containers to it"""
    pass


init(autoreset=True)

cli.add_command(create.create)
cli.add_command(destroy.destroy)
cli.add_command(configure.configure_keys)

cli.add_command(docker.docker)
cli.add_command(compute.compute)
cli()