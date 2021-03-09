import click
from colorama import init

from cli import \
    config, \
    destroy, \
    compute, \
    docker, \
    doctor


@click.group()
def cli():
    """This script allows you to setup Numer.ai compute node and deploy docker containers to it"""
    pass


def main():
    init(autoreset=True)

    cli.add_command(compute.compute)
    cli.add_command(config.config)
    cli.add_command(destroy.destroy)
    cli.add_command(docker.docker)
    cli.add_command(doctor.doctor)
    cli()


if __name__ == '__main__':
    main()
