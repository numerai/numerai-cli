from os import path
import json

import click

from cli.util import \
    copy_files, \
    get_project_numerai_dir, \
    get_code_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.configure import load_or_configure_app, PROVIDER_AWS, DEFAULT_CPU, DEFAULT_MEMORY

@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--cpu', '-c', type=int,
    help=f"Amount of CPU credits (cores * 1024) to use in the compute container (defaults to {DEFAULT_CPU}). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings")
@click.option(
    '--memory', '-m', type=int,
    help=f"Amount of Memory (in MiB) to use in the compute container (defaults to {DEFAULT_MEMORY}). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings")
@click.option(
    '--provider', '-p', type=str, default=PROVIDER_AWS,
    help="Select a cloud provider. One of ['aws']. Defaults to 'aws'.")
@click.option(
    '--app', '-a', type=str, default='default',
    help="Create/configure an app, defaults to 'default'.")
@click.option(
    '--update', '-u', is_flag=True,
    help="Update files in .numerai (terraform, lambda zips, and other copied files)")
def create(verbose, cpu, memory, provider, app, update):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    Will output two important URLs at the end of running:
        - submission_url:   The webhook url you will provide to Numerai.
                            A copy is stored in .numerai/submission_url.txt.

        - docker_repo:      Used for "numerai docker ..."
    """
    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir) or update:
        copy_files(
            path.join(get_code_dir(), "terraform"),
            get_project_numerai_dir(),
            force=True,
            verbose=verbose
        )
    numerai_dir = format_path_if_mingw(numerai_dir)

    config = load_or_configure_app(provider)
    config.configure_app(app, provider, cpu, memory)

    # terraform init
    run_terraform_cmd("init -upgrade", config, numerai_dir, verbose)
    click.echo('succesfully setup .numerai with terraform')

    # terraform apply
    run_terraform_cmd(
        f'apply -auto-approve -var="app_config_file=apps.json"',
        config, numerai_dir, verbose, env_vars=config.provider_keys(app))
    click.echo('successfully created cloud resources')

    # terraform output for AWS apps
    click.echo('retrieving application configs')
    aws_applications = json.loads(run_terraform_cmd(
        f"output -json aws_applications", config, numerai_dir, verbose, pipe_output=False
    ).stdout.decode('utf-8'))
    config.configure_outputs(aws_applications)
