import os
import base64
import subprocess

import boto3

import click
from colorama import Fore

from cli.util import copy_files, get_code_dir, format_path_if_mingw
from cli.configure import Config


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


def docker_build(config, verbose):

    c = f'docker build -t {config.docker_repo} --build-arg NUMERAI_PUBLIC_ID={config.numerai_public} --build-arg NUMERAI_SECRET_KEY={config.numerai_secret} .'
    if verbose:
        click.echo("running: " + config.sanitize_message(c))

    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--command', '-c', default='python train.py', type=(str),
              help="Defines the command to run inside the docker container.")
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def train(command, verbose, app):
    """
    Run the docker image locally and output trained models.
    Assumes a file called `train.py` exists and runs it by default.
    Serializes your model to this directory.
    See the example if you want inspiration for how to do this.
    """
    config = Config()
    docker_build(config, verbose)
    cur_dir = format_path_if_mingw(os.getcwd())

    c = f'docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {config.docker_repo} {command}'
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def run(verbose, app):
    """
    Run the docker image locally and submit predictions.
    This runs the default CMD in your docker container (example uses predict.py / main.R)
    """
    config = Config()
    docker_build(config, verbose)

    cur_dir = format_path_if_mingw(os.getcwd())

    c = f'docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {config.docker_repo} '
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def build(verbose):
    """Builds the docker image"""
    config = Config()
    docker_build(config, verbose)


def docker_cleanup(config, verbose):

    ecr_client = boto3.client(
        'ecr', region_name='us-east-1',
        aws_access_key_id=config.aws_public,
        aws_secret_access_key=config.aws_secret)

    resp = ecr_client.list_images(repositoryName='numerai-submission',
                                  filter={
                                      'tagStatus': 'UNTAGGED',
                                  })

    imageIds = resp['imageIds']
    if len(imageIds) == 0:
        return

    resp = ecr_client.batch_delete_image(
        repositoryName='numerai-submission',
        imageIds=imageIds)

    imageIds = resp['imageIds']
    if len(imageIds) > 0:
        click.echo(Fore.YELLOW + "deleted " + str(len(imageIds)) +
                   " old image(s) from remote docker repo")


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def cleanup(verbose):
    config = Config()
    docker_cleanup(config, verbose)


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
# @click.option(
#     '--app', '-a', type=str, default='default',
#     help="Target a different app other than 'default'")
def deploy(verbose):
    """Builds and pushes your docker image to the AWS ECR repo"""
    config = Config()
    docker_build(config, verbose)

    ecr_client = boto3.client('ecr',
                              region_name='us-east-1',
                              aws_access_key_id=config.aws_public,
                              aws_secret_access_key=config.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']
    ).decode().split(':')

    if verbose:
        click.echo('running: docker login')
    res = subprocess.run(
        f'docker login -u {username} -p {password} {config.docker_repo}',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    res.check_returncode()

    c = f'docker push {config.docker_repo}'
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()

    docker_cleanup(config, verbose)