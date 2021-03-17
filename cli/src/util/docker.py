import sys
import subprocess
import base64

import boto3

from cli.src.constants import *
from cli.src.util.files import load_or_init_nodes, format_path_if_mingw
from cli.src.util.debug import root_cause
from cli.src.util.keys import sanitize_message, get_aws_keys, load_or_init_keys


def execute(command, verbose):
    res = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if not verbose:
        pass
    elif res.stdout:
        click.echo(res.stdout.decode('utf8'))
    elif res.stderr:
        click.secho(res.stderr.decode('utf8'), fg='red', file=sys.stderr)

    if res.returncode != 0:
        root_cause(res.stderr)

        if not verbose:
            click.secho(
                "An unexpected error occurred, try running this command again "
                "with the '--verbose|-v' flag to get more information", fg='red'
            )

    return res


def terraform(tf_cmd, verbose, env_vars=None, version='0.14.3'):
    cmd = f"docker run"
    if env_vars:
        for key, val in env_vars.items():
            cmd += f' -e "{key}={val}"'
    cmd += f' --rm -it -v {CONFIG_PATH}:/opt/plan'
    cmd += f' -w /opt/plan hashicorp/terraform:{version} {tf_cmd}'

    if verbose:
        click.echo('Running: ' + sanitize_message(cmd))

    # in case of an 'output' command
    return execute(cmd, verbose)


def build(node_config, verbose):
    numerai_keys = load_or_init_keys()['numerai']

    build_arg_str = ''
    for arg in numerai_keys:
        build_arg_str += f' --build-arg {arg}={numerai_keys[arg]}'

    cmd = f'docker build -t {node_config["docker_repo"]} ' \
          f'{build_arg_str} {node_config["path"]}'
    if verbose:
        click.echo("running: " + sanitize_message(cmd))

    execute(cmd, verbose)


def run(node_config, verbose, command=''):
    cmd = f"docker run --rm -it -v {node_config['path']}:/opt/app " \
          f"-w /opt/app {node_config['docker_repo']} {command}"
    if verbose:
        click.echo('running: ' + cmd)

    execute(cmd, verbose)


def login(node_config, verbose):
    if node_config['provider'] == PROVIDER_AWS:
        username, password = login_aws()

    else:
        raise ValueError(f"Unsupported provider: '{node_config['provider']}'")
    cmd = f"docker login -u {username} -p {password} {node_config['docker_repo']}"

    execute(cmd, verbose)


def login_aws():
    aws_public, aws_secret = get_aws_keys()
    ecr_client = boto3.client(
        'ecr', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']
    ).decode().split(':')

    return username, password


def push(docker_repo, verbose):
    cmd = f'docker push {docker_repo}'
    execute(cmd, verbose)


def cleanup(node_config):
    provider = node_config['provider']
    if provider == PROVIDER_AWS:
        imageIds = cleanup_aws(node_config['docker_repo'])

    else:
        raise ValueError(f"Unsupported provider: '{provider}'")

    if len(imageIds) > 0:
        click.secho(f"Deleted {str(len(imageIds))} old image(s) from remote docker repo", fg='yellow')


def cleanup_aws(docker_repo):
    aws_public, aws_secret = get_aws_keys()
    ecr_client = boto3.client(
        'ecr', region_name='us-east-1',
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret)

    docker_repo_name = docker_repo.split("/")[-1]

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