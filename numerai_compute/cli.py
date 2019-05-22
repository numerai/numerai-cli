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


@click.group()
def cli():
    pass


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

    subprocess.call(
        f"docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light init", shell=True)

    subprocess.call(
        f'''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve''', shell=True)

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

    subprocess.call(
        f'''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light destroy -auto-approve''', shell=True)


@click.command()
def setup():
    terraform_setup()


@click.command()
def destroy():
    terraform_destroy()


@click.command()
def copy_docker_example():
    copy_docker_python3()


@click.command()
def docker_build():
    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    subprocess.call(
        f'''docker build -t {docker_repo} --build-arg NUMERAI_PUBLIC_ID={keys.numerai_public} --build-arg NUMERAI_SECRET_KEY={keys.numerai_secret} .''', shell=True)


@click.command()
def docker_run():
    docker_repo = read_docker_repo_file()

    subprocess.call(
        f'''docker run {docker_repo}''', shell=True)


@click.command()
def docker_deploy():
    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    ecr_client = boto3.client('ecr', region_name='us-east-1',
                              aws_access_key_id=keys.aws_public, aws_secret_access_key=keys.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']).decode().split(':')

    subprocess.run(
        f'''docker login -u {username} -p {password} {docker_repo}''', shell=True)
    subprocess.call(
        f'''docker push {docker_repo}''', shell=True)


def main():
    cli.add_command(setup)
    cli.add_command(destroy)
    cli.add_command(copy_docker_example)
    cli.add_command(docker_build)
    cli.add_command(docker_run)
    cli.add_command(docker_deploy)
    cli()


if __name__ == "__main__":
    main()
