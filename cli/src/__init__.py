import click
from colorama import init

from cli.src import util, constants, doctor, node, setup, uninstall, upgrade
from cli.src.util import docker, files, keys


@click.group()
def numerai():
    """
    This tool helps you setup Numer.ai Prediction Nodes and deploy your models to them.
    """
    pass


def main():
    init(autoreset=True)

    numerai.add_command(setup.setup)
    numerai.add_command(node.node)
    numerai.add_command(doctor.doctor)
    numerai.add_command(uninstall.uninstall)
    numerai.add_command(upgrade.upgrade)
    numerai()
