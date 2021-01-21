import os
import base64
import subprocess

import boto3
import click

from cli.util import copy_files, get_code_dir, format_path_if_mingw
from cli.configure import Config, PROVIDER_AWS


@click.group()
def docker():
    """Docker commands for building/deploying an image."""
    pass


@docker.command()
@click.option('--quiet', '-q', is_flag=True)
@click.option('--force', '-f', is_flag=True)
@click.option('--rlang', '-r', is_flag=True, help='Copy the RLang example.')
def copy_example(quiet, force, rlang):
    """
    Copies all example files into the current directory.

    WARNING: this will overwrite the following files if they exist:
        - Python: Dockerfile, model.py, train.py, predict.py, and requirements.txt
        - RLang:  Dockerfile, install_packages.R, main.R
    """
    if rlang:
        example_dir = os.path.join(get_code_dir(), "examples", "rlang")
    else:
        example_dir = os.path.join(get_code_dir(), "examples", "python3")
    copy_files(example_dir, '.', force, not quiet)

    with open('.dockerignore', 'a+') as f:
        f.write(".numerai\n")
        f.write("numerai_dataset.zip\n")
        f.write(".git\n")


def docker_build(config, verbose, app, build_args=None):
    build_arg_str = ''
    for arg in build_args:
        build_arg_str += f' --build-arg {arg}={build_args[arg]}'
    cmd = f'docker build -t {config.docker_repo(app)} {build_arg_str} .'
    if verbose:
        click.echo("running: " + config.sanitize_message(cmd))
    res = subprocess.run(cmd, shell=True)
    res.check_returncode()


@docker.command()
@click.option(
    '--command', '-c', type=str, default='python train.py',
    help="Defines the command to run inside the docker container.")
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def train(command, verbose, app):
    """
    Run the docker image locally and output trained models.
    Assumes a file called `train.py` exists and runs it by default.
    Serializes your model to this directory.
    See the example if you want inspiration for how to do this.
    """
    config = Config()
    docker_build(config, verbose, app, build_args=config.numerai_keys)
    cur_dir = format_path_if_mingw(os.getcwd())

    c = f'docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {config.docker_repo(app)} {command}'
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def run(verbose, app):
    """
    Run the docker image locally and submit predictions.
    This runs the default CMD in your docker container (example uses predict.py / main.R)
    """
    config = Config()
    docker_build(config, verbose, app, build_args=config.numerai_keys)

    cur_dir = format_path_if_mingw(os.getcwd())

    c = f'docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {config.docker_repo(app)} '
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def build(verbose, app):
    """Builds the docker image"""
    config = Config()
    docker_build(config, verbose, app, build_args=config.numerai_keys)


def docker_cleanup_aws(config, app):
    ecr_client = boto3.client(
        'ecr', region_name='us-east-1',
        aws_access_key_id=config.aws_public,
        aws_secret_access_key=config.aws_secret)

    docker_repo_name = config.docker_repo(app).split("/")[-1]

    resp = ecr_client.list_images(
        repositoryName=docker_repo_name,
        filter={'tagStatus': 'UNTAGGED'})

    imageIds = resp['imageIds']
    if len(imageIds) == 0:
        return []

    resp = ecr_client.batch_delete_image(
        repositoryName=docker_repo_name,
        imageIds=imageIds)

    return resp['imageIds']


def docker_cleanup(config, verbose, app):
    provider = config.provider(app)
    if provider == PROVIDER_AWS:
        imageIds = docker_cleanup_aws(config, app)

    else:
        click.secho(f"Unsupported provider: '{provider}'", fg='red')
        return

    if len(imageIds) > 0:
        click.secho(f"Deleted {str(len(imageIds))} old image(s) from remote docker repo", fg='yellow')


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def cleanup(verbose, app):
    config = Config()
    docker_cleanup(config, verbose, app)


def docker_login_aws(config):
    ecr_client = boto3.client(
        'ecr', region_name='us-east-1',
        aws_access_key_id=config.aws_public,
        aws_secret_access_key=config.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']
    ).decode().split(':')

    return username, password


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--app', '-a', type=str, default='default',
    help="Target a different app other than 'default'")
def deploy(verbose, app):
    """Builds and pushes your docker image to the AWS ECR repo"""
    config = Config()
    docker_build(config, verbose, app, build_args=config.numerai_keys)

    provider = config.provider(app)
    if provider == PROVIDER_AWS:
        username, password = docker_login_aws(config)
    else:
        click.secho(f"Unsupported provider: '{provider}'", fg='red')
        return

    if verbose:
        click.echo('running: docker login')
    docker_repo = config.docker_repo(app)
    res = subprocess.run(
        f'docker login -u {username} -p {password} {docker_repo}',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    res.check_returncode()

    c = f'docker push {docker_repo}'
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()

    docker_cleanup(config, verbose, app)