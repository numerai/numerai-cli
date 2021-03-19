import click
from colorama import init

from numerai.cli import \
    constants, \
    doctor, \
    node, \
    setup, \
    uninstall, \
    upgrade, \
    misc
from numerai.cli.util import \
    debug, \
    docker, \
    files, \
    keys


@click.group()
def numerai():
    """
    This tool helps you setup Numer.ai Prediction Nodes and deploy your models to them.
    """
    pass


def main():
    if debug.is_win8():
        init(wrap=False)
    else:
        init(autoreset=True)

    numerai.add_command(setup.setup)
    numerai.add_command(node.node)
    numerai.add_command(doctor.doctor)
    numerai.add_command(uninstall.uninstall)
    numerai.add_command(upgrade.upgrade)
    numerai.add_command(misc.copy_example)
    numerai.add_command(constants.size_presets)
    numerai()
