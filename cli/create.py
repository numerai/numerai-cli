from os import path
import json

import click

from cli.util import \
    copy_files, \
    get_project_numerai_dir, \
    get_code_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.configure import load_or_configure_app, get_app_config_path


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--cpu', '-c', type=int,
    help="Amount of CPU credits (cores * 1024) to use in the compute container (defaults to 1024). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings"
)
@click.option(
    '--memory', '-m', type=int,
    help="Amount of Memory (in MiB) to use in the compute container (defaults to 8192). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings"
)
@click.option(
    '--provider', '-p', type=str,
    help="Select a cloud provider, defaults to 'aws'. One of ['aws']"
)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'"
)
@click.option('--update', '-u', is_flag=True)
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

    config = load_or_configure_app()
    config.configure_app(app, provider, cpu, memory)

    # terraform init
    run_terraform_cmd("init -upgrade", config, numerai_dir, verbose)
    click.echo('succesfully setup .numerai with terraform')

    # terraform apply
    cmd = f'apply -auto-approve -var="app_config_file=apps.json"'
    run_terraform_cmd(cmd, config, numerai_dir, verbose, env_vars=config.provider_keys(app))

    # terraform output
    webhook_url_res = run_terraform_cmd(f"output submission_url", config, numerai_dir, verbose).stdout.decode('utf-8')
    docker_repos_obj = run_terraform_cmd(f"output docker_repos", config, numerai_dir, verbose).stdout.decode('utf-8')

    config.configure_urls(
        webhook_url_res.strip().replace('"', ''),
        json.loads(docker_repos_obj.replace("=", ":"))
    )
