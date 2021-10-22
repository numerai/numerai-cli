import sys
import base64
import subprocess
from queue import Queue, Empty
from threading import Thread

import boto3
import click

from numerai.cli.constants import *
from numerai.cli.util.debug import root_cause
from numerai.cli.util.keys import sanitize_message, get_aws_keys, load_or_init_keys


def check_for_dockerfile(path):
    dockerfile_path = os.path.join(path, 'Dockerfile')
    if not os.path.exists(dockerfile_path):
        click.secho(
            f"No Dockerfile found in {path}, please ensure this node "
            f"was created from an example or follows the Prediction Node Architecture. "
            f"Learn More:\nhttps://github.com/numerai/numerai-cli/wiki/Prediction-Nodes",
            fg='red'
        )
        exit(1)
    if Path.home() == dockerfile_path:
        click.secho(
            f"DO NOT PUT THE DOCKERFILE IN YOUR HOME PATH, please ensure this node "
            f"was created from an example or follows the Prediction Node Architecture. "
            f"Learn More:\nhttps://github.com/numerai/numerai-cli/wiki/Prediction-Nodes",
            fg='red'
        )
        exit(1)


def subprocess_log(stream, queue):
    for line in iter(stream.readline, b''):
        queue.put(line)
    stream.close()


def get_from_q(q, verbose, default=b'', prefix=''):
    try:
        res = q.get(block=False)
        if verbose and res:
            click.secho(f'{prefix} {res.decode()}')
        return res
    except Empty as e:
        return default


def execute(command, verbose, censor_substr=None):
    if verbose:
        click.echo('Running: ' + sanitize_message(command, censor_substr))

    on_posix = 'posix' in sys.builtin_module_names
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        close_fds=on_posix
    )
    stdout_q = Queue()
    stderr_q = Queue()
    stdout_t = Thread(
        target=subprocess_log,
        args=(proc.stdout, stdout_q)
    )
    stderr_t = Thread(
        target=subprocess_log,
        args=(proc.stderr, stderr_q)
    )

    try:
        stdout_t.start()
        stderr_t.start()
        stdout = b''
        stderr = b''
        while proc.poll() is None:
            stdout += get_from_q(stdout_q, verbose)
            stderr += get_from_q(stderr_q, verbose)

        returncode = proc.poll()
        if returncode != 0:
            root_cause(stdout, stderr)
    finally:
        stdout_t.join()
        stderr_t.join()
        proc.kill()

    return stdout, stderr


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
    stdout, stderr = execute(cmd, verbose)
    # if user accidently deleted a resource, refresh terraform and try again
    if b'ResourceNotFoundException' in stdout or b'NoSuchEntity' in stdout:
        refresh = build_tf_cmd('refresh', env_vars, inputs, version, verbose)
        execute(refresh, verbose)
        stdout, stderr = execute(cmd, verbose)
    return stdout


def build(node_config, verbose):
    numerai_keys = load_or_init_keys()['numerai']

    node_path = node_config["path"]
    curr_path = os.path.abspath('.')
    if curr_path not in node_path:
        raise RuntimeError(
            f'Current directory invalid, you must run this command either from'
            f' "{node_path}" or a parent directory of that path.'
        )
    path = format_if_docker_toolbox(node_path.replace(curr_path, '.'), verbose)
    dockerfile_path = format_if_docker_toolbox(f'{path}/Dockerfile', verbose)
    print(f'formatted node path {node_path} to {path}')

    build_arg_str = ''
    for arg in numerai_keys:
        build_arg_str += f' --build-arg {arg}={numerai_keys[arg]}'
    build_arg_str += f' --build-arg MODEL_ID={node_config["model_id"]}'
    build_arg_str += f' --build-arg SRC_PATH={path}'

    cmd = f'docker build -t {node_config["docker_repo"]}' \
          f'{build_arg_str} -f {dockerfile_path} .'

    execute(cmd, verbose)


def run(node_config, verbose, command=''):
    cmd = f"docker run --rm -it {node_config['docker_repo']} {command}"
    execute(cmd, verbose)


def login(node_config, verbose):
    if node_config['provider'] == PROVIDER_AWS:
        username, password = login_aws()

    else:
        raise ValueError(f"Unsupported provider: '{node_config['provider']}'")
    cmd = (
        f"echo '{password}'"
        f" | docker login"
        f" -u {username}"
        f" --password-stdin"
        f" {node_config['docker_repo']}"
    )

    execute(cmd, verbose, censor_substr=password)


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
    execute(cmd, verbose=verbose)


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