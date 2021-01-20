import os

import click
from colorama import Fore

from cli.util import \
    get_project_numerai_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.configure import load_or_configure_app


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'"
)
def destroy(verbose, app):
    """
    Uses Terraform to destroy Numerai Compute cluster in AWS.
    This will delete everything, including:
        - lambda url
        - docker container and associated task
        - all logs
    This command is idempotent and safe to run multiple times.
    """
    numerai_dir = get_project_numerai_dir()
    if not os.path.exists(numerai_dir):
        click.echo(f"{Fore.RED} .numerai directory not setup, run 'numerai create' first...")
    numerai_dir = format_path_if_mingw(numerai_dir)

    config = load_or_configure_app()

    cmd = f'destroy -auto-approve'
    run_terraform_cmd(cmd, config, numerai_dir, verbose, env_vars=config.provider_keys(app))
