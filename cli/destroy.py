import os

import click

from cli.util import \
    get_project_numerai_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.config import Config


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--node', '-n', type=str, default='default',
    help="Target a node. Defaults to 'default'.")
def destroy(verbose, node):
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
        click.secho(f".numerai directory not setup, run 'numerai create' first...", fg='red')
        return
    numerai_dir = format_path_if_mingw(numerai_dir)

    try:
        config = Config()
        provider_keys = config.provider_keys(node)

        click.secho(f"deleting node configuration...")
        config.delete_app(node)
        cmd = f'destroy -auto-approve'
        click.secho(f"deleting cloud resources...")
        run_terraform_cmd(cmd, config, numerai_dir, verbose, env_vars=provider_keys)

    except (KeyError, FileNotFoundError):
        click.secho(f"run `numerai create` first...", fg='red')
        return
