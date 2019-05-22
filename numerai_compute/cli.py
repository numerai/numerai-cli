import numerai_compute
import click
from pathlib import Path
import os
from os import path
import configparser
import shutil
import subprocess
import base64
import boto3


def get_key_file():
    home = str(Path.home())

    return path.join(home, '.numerai')


class KeyConfig:
    def __init__(self, aws_public, aws_secret, numerai_public, numerai_secret):
        self._aws_public = aws_public
        self._aws_secret = aws_secret
        self._numerai_public = numerai_public
        self._numerai_secret = numerai_secret

    @property
    def aws_public(self):
        return self._aws_public

    @property
    def aws_secret(self):
        return self._aws_secret

    @property
    def numerai_public(self):
        return self._numerai_public

    @property
    def numerai_secret(self):
        return self._numerai_secret


def load_keys():
    key_file = get_key_file()

    config = configparser.ConfigParser()
    config.read(key_file)

    return KeyConfig(
        aws_public=config['default']['AWS_ACCESS_KEY_ID'],
        aws_secret=config['default']['AWS_SECRET_ACCESS_KEY'],
        numerai_public=config['default']['NUMERAI_PUBLIC_ID'],
        numerai_secret=config['default']['NUMERAI_SECRET_KEY'])


def load_or_setup_keys():
    try:
        return load_keys()
    except:
        click.echo("Key file not found at: " + get_key_file())

    return setup_keys()


def setup_keys():
    click.echo("Setting up key file at " + get_key_file())

    click.echo("Please type in the following keys:")
    aws_public = click.prompt('AWS_ACCESS_KEY_ID', hide_input=True).strip()
    aws_private = click.prompt(
        'AWS_SECRET_ACCESS_KEY', hide_input=True).strip()
    numerai_public = click.prompt('NUMERAI_PUBLIC_ID', hide_input=True).strip()
    numerai_private = click.prompt(
        'NUMERAI_SECRET_KEY', hide_input=True).strip()

    config = configparser.ConfigParser()
    config['default'] = {
        "AWS_ACCESS_KEY_ID": aws_public,
        "AWS_SECRET_ACCESS_KEY": aws_private,
        "NUMERAI_PUBLIC_ID": numerai_public,
        "NUMERAI_SECRET_KEY": numerai_private,
    }

    with open(get_key_file(), 'w') as configfile:
        config.write(configfile)

    return load_keys()


def get_code_dir():
    return path.dirname(__file__)


def get_project_numerai_dir():
    return path.join(os.getcwd(), ".numerai")


def get_docker_repo_file():
    return path.join(get_project_numerai_dir(), 'docker_repo.txt')


def get_submission_url_file():
    return path.join(get_project_numerai_dir(), 'submission_url.txt')


def read_docker_repo_file():
    with open(get_docker_repo_file(), 'r') as f:
        return f.read().strip()


def copy_terraform():
    click.echo("Creating .numerai directory in current project")
    shutil.copytree(path.join(get_code_dir(), "terraform"),
                    get_project_numerai_dir(), copy_function=shutil.copy)


def copy_docker_python3():
    click.echo("copying Dockerfile")
    shutil.copy(path.join(get_code_dir(), "examples",
                          "python3", "Dockerfile"), "Dockerfile")
    click.echo("copying main.py")
    shutil.copy(path.join(get_code_dir(), "examples",
                          "python3", "main.py"), "main.py")
    click.echo("copying requirements.txt")
    shutil.copy(path.join(get_code_dir(), "examples",
                          "python3", "requirements.txt"), "requirements.txt")


def terraform_setup():
    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        copy_terraform()

    keys = load_or_setup_keys()

    res = subprocess.run(
        f"docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light init", shell=True)
    res.check_returncode()

    res = subprocess.run(
        f'''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve''', shell=True)
    res.check_returncode()

    res = subprocess.run(
        f'''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output docker_repo''', shell=True, stdout=subprocess.PIPE)

    with open(get_docker_repo_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())

    res = subprocess.run(
        f'''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output submission_url''', shell=True, stdout=subprocess.PIPE)

    with open(get_submission_url_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())


def terraform_destroy():
    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        return

    keys = load_or_setup_keys()

    res = subprocess.run(
        f'''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light destroy -auto-approve''', shell=True)
    res.check_returncode()


@click.group()
def cli():
    """This script allows you to setup Numer.ai compute node and deploy docker containers to it"""
    pass


@click.command()
def setup():
    """Sets up a Numer.ai compute node in AWS"""
    terraform_setup()


@click.command()
def destroy():
    """Destroys a previously setup Numer.ai compute node"""
    terraform_destroy()


@click.group()
def docker():
    """A collection of docker commands for building/deploying a docker image"""
    pass


@docker.command()
def copy_example():
    """Copies a few example files into the current directory"""
    copy_docker_python3()


@docker.command()
def run():
    """
    Run the docker image locally.

    Requires that `build` has already run and succeeded. Useful for local testing of the docker container
    """
    docker_repo = read_docker_repo_file()

    res = subprocess.run(
        f'''docker run {docker_repo}''', shell=True)
    res.check_returncode()


@docker.command()
def build():
    """Builds the docker image"""
    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    res = subprocess.run(
        f'''docker build -t {docker_repo} --build-arg NUMERAI_PUBLIC_ID={keys.numerai_public} --build-arg NUMERAI_SECRET_KEY={keys.numerai_secret} .''', shell=True)
    res.check_returncode()


@docker.command()
def deploy():
    """Deploy the docker image to the Numer.ai compute node"""
    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    ecr_client = boto3.client('ecr', region_name='us-east-1',
                              aws_access_key_id=keys.aws_public, aws_secret_access_key=keys.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']).decode().split(':')

    res = subprocess.run(
        f'''docker login -u {username} -p {password} {docker_repo}''', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res.check_returncode()

    res = subprocess.run(
        f'''docker push {docker_repo}''', shell=True)
    res.check_returncode()


def main():
    cli.add_command(setup)
    cli.add_command(destroy)

    cli.add_command(docker)
    cli()


if __name__ == "__main__":
    main()
