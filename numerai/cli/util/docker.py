import base64
import subprocess
import sys

import boto3
import click

from numerai.cli.constants import *
from numerai.cli.util.debug import root_cause
from numerai.cli.util.keys import sanitize_message, get_aws_keys, load_or_init_keys


def execute(command, verbose):
    if verbose:
        click.echo('Running: ' + sanitize_message(command))

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
        root_cause(res)

    return res


def format_if_docker_toolbox(path, verbose):
    '''
    Helper function to format if the system is running docker toolbox + mingw.
    Paths need to be formatted like unix paths, and the drive letter lower-cased
    '''
    if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ and 'MSYSTEM' in os.environ:
        # '//' found working on win8.1 docker quickstart terminal, previously just '/'
        new_path = ('//' + path[0].lower() + path[2:]).replace('\\', '/')
        if verbose:
            click.secho(f"formatted path for docker toolbox: {path} -> {new_path}")
        return new_path
    return path


def build_tf_cmd(tf_cmd, env_vars, inputs, version, verbose):
    cmd = f"docker run"
    if env_vars:
        cmd += ' '.join([f' -e "{key}={val}"' for key, val in env_vars.items()])
    cmd += f' --rm -it -v {format_if_docker_toolbox(CONFIG_PATH, verbose)}:/opt/plan'
    cmd += f' -w /opt/plan hashicorp/terraform:{version} {tf_cmd}'
    if inputs:
        cmd += ' '.join([f' -var="{key}={val}"' for key, val in inputs.items()])
    return cmd


def terraform(tf_cmd, verbose, env_vars=None, inputs=None, version='0.14.3'):
    cmd = build_tf_cmd(tf_cmd, env_vars, inputs, version, verbose)
    res = execute(cmd, verbose)
    # if user accidently deleted a resource, refresh terraform and try again
    if b'ResourceNotFoundException' in res.stdout or b'NoSuchEntity' in res.stdout:
        refresh = build_tf_cmd('refresh', env_vars, inputs, version, verbose)
        execute(refresh, verbose)
        res = execute(cmd, verbose)
    return res


def build(node_config, verbose):
    numerai_keys = load_or_init_keys()['numerai']

    build_arg_str = ''
    for arg in numerai_keys:
        build_arg_str += f' --build-arg {arg}={numerai_keys[arg]}'

    cmd = f'docker build -t {node_config["docker_repo"]} ' \
          f'{build_arg_str} {node_config["path"]}'

    execute(cmd, verbose)


def run(node_config, verbose, command=''):
    cmd = f"docker run --rm -it -v " \
          f"{format_if_docker_toolbox(node_config['path'], verbose)}:/opt/app " \
          f"-w /opt/app {node_config['docker_repo']} {command}"

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