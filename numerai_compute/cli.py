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
import numerapi
from colorama import init, Fore, Back, Style


def exception_with_msg(msg):
    return click.ClickException(Fore.RED + msg)


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

    def sanitize_message(self, message):
        return message.replace(self.aws_public, '...').replace(self.aws_secret, '...').replace(self.numerai_public, '...').replace(self.numerai_secret, '...')


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


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id,
                              aws_secret_access_key=secret)
        client.list_buckets()
        return True

    except Exception as e:
        if 'NotSignedUp' in str(e):
            raise exception_with_msg(
                '''Your AWS keys are valid, but the account is not finished signing up. You either need to update your credit card in AWS at https://portal.aws.amazon.com/billing/signup?type=resubscribe#/resubscribed, or wait up to 24 hours for their verification process to complete.''')

        raise exception_with_msg(
            '''AWS keys seem to be invalid. Make sure you've entered them correctly and that your user has the "AdministratorAccess" policy.''')


def check_numerai_validity(key_id, secret):
    try:
        napi = numerapi.NumerAPI(key_id, secret)
        napi.get_user()
        return True

    except Exception:
        raise exception_with_msg(
            '''Numerai keys seem to be invalid. Make sure you've entered them correctly.''')


def setup_keys():
    click.echo(Fore.YELLOW + "Setting up key file at " + get_key_file())

    click.echo()
    click.echo(Fore.RED + "Please type in the following keys:")
    aws_public = click.prompt('AWS_ACCESS_KEY_ID').strip()
    aws_private = click.prompt(
        'AWS_SECRET_ACCESS_KEY').strip()
    numerai_public = click.prompt('NUMERAI_PUBLIC_ID').strip()
    numerai_private = click.prompt(
        'NUMERAI_SECRET_KEY').strip()

    config = configparser.ConfigParser()
    config['default'] = {
        "AWS_ACCESS_KEY_ID": aws_public,
        "AWS_SECRET_ACCESS_KEY": aws_private,
        "NUMERAI_PUBLIC_ID": numerai_public,
        "NUMERAI_SECRET_KEY": numerai_private,
    }

    check_aws_validity(aws_public, aws_private)
    check_numerai_validity(numerai_public, numerai_private)

    with open(get_key_file(), 'w') as configfile:
        config.write(configfile)

    return load_keys()


def get_code_dir():
    return path.dirname(__file__)


def format_path_if_mingw(p):
    '''
    Helper function to format if the system is running docker toolbox + mingw. The paths need to be formatted like unix paths, and the drive letter needs to be lowercased
    '''
    if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ and 'MSYSTEM' in os.environ:
        p = '/' + p[0].lower() + p[2:]
        p = p.replace('\\', '/')
    return p


def get_project_numerai_dir():
    return path.join(os.getcwd(), ".numerai")


def get_docker_repo_file():
    return path.join(get_project_numerai_dir(), 'docker_repo.txt')


def get_submission_url_file():
    return path.join(get_project_numerai_dir(), 'submission_url.txt')


def read_docker_repo_file():
    docker_file = get_docker_repo_file()
    if not path.exists(docker_file):
        raise exception_with_msg(
            "docker repo not found. Make sure you have run `numerai setup` successfully before running this command.")

    with open(docker_file, 'r') as f:
        return f.read().strip()


def copy_terraform():
    click.echo("Creating .numerai directory in current project")
    shutil.copytree(path.join(get_code_dir(), "terraform"),
                    get_project_numerai_dir(), copy_function=shutil.copy)


def copy_file(verbose, directory, filename):
    if verbose:
        click.echo(Fore.YELLOW + "copying " + filename)
    shutil.copy(path.join(directory, filename), filename)


def copy_docker_python3(verbose):
    code_dir = path.join(get_code_dir(), "examples", "python3")
    copy_file(verbose, code_dir, "Dockerfile")
    copy_file(verbose, code_dir, "model.py")
    copy_file(verbose, code_dir, "train.py")
    copy_file(verbose, code_dir, "predict.py")
    copy_file(verbose, code_dir, "requirements.txt")


def copy_docker_rlang(verbose):
    code_dir = path.join(get_code_dir(), "examples", "rlang")
    copy_file(verbose, code_dir, "Dockerfile")
    copy_file(verbose, code_dir, "install_packages.R")
    copy_file(verbose, code_dir, "main.R")


def terraform_setup(verbose):
    if path.abspath(os.getcwd()) == path.abspath(str(Path.home())):
        raise exception_with_msg(
            "`numerai setup` cannot be run from your $HOME directory. Please create another directory and run this again.")

    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        copy_terraform()
    # Format path for mingw after checking that it exists
    numerai_dir = format_path_if_mingw(numerai_dir)

    keys = load_or_setup_keys()

    c = "docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light init".format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True)
    res.check_returncode()

    c = '''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True)
    res.check_returncode()

    c = '''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output docker_repo'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True, stdout=subprocess.PIPE)

    with open(get_docker_repo_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())
    click.echo(Fore.YELLOW + 'wrote docker repo to: ' + get_docker_repo_file())

    c = '''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output submission_url'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True, stdout=subprocess.PIPE)

    with open(get_submission_url_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())
    click.echo(Fore.YELLOW + 'wrote submission url to: ' +
               get_submission_url_file())


def terraform_destroy(verbose):
    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        return
    numerai_dir = format_path_if_mingw(numerai_dir)

    keys = load_or_setup_keys()

    c = '''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light destroy -auto-approve'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@click.group()
def cli():
    """This script allows you to setup Numer.ai compute node and deploy docker containers to it"""
    pass


@click.command()
@click.option('--verbose', '-v', is_flag=True)
def setup(verbose):
    """Sets up a Numer.ai compute node in AWS"""
    terraform_setup(verbose)


@click.command()
@click.option('--verbose', '-v', is_flag=True)
def destroy(verbose):
    """Destroys a previously setup Numer.ai compute node"""
    terraform_destroy(verbose)


@click.group()
def docker():
    """A collection of docker commands for building/deploying a docker image"""
    pass


@docker.command()
@click.option('--quiet', '-q', is_flag=True)
@click.option('--rlang', '-r', is_flag=True)
def copy_example(quiet, rlang):
    """Copies a few example files into the current directory"""
    if rlang:
        copy_docker_rlang(not quiet)
    else:
        copy_docker_python3(not quiet)

    with open('.dockerignore', 'a+') as f:
        f.write(".numerai\n")
        f.write("numerai_dataset.zip\n")


def docker_build(verbose):
    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    c = '''docker build -t {docker_repo} --build-arg NUMERAI_PUBLIC_ID={keys.numerai_public} --build-arg NUMERAI_SECRET_KEY={keys.numerai_secret} .'''.format(
        **locals())
    if verbose:
        click.echo("running: " + keys.sanitize_message(c))

    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--command', '-c', default='python train.py', type=(str))
@click.option('--verbose', '-v', is_flag=True)
def train(command, verbose):
    """
    Run the docker image locally.

    Requires that `build` has already run and succeeded. Useful for local testing of the docker container
    """
    docker_build(verbose)

    docker_repo = read_docker_repo_file()
    cur_dir = format_path_if_mingw(os.getcwd())

    c = '''docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {docker_repo} {command}'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def run(verbose):
    """
    Run the docker image locally.

    Requires that `build` has already run and succeeded. Useful for local testing of the docker container
    """
    docker_build(verbose)

    docker_repo = read_docker_repo_file()
    cur_dir = format_path_if_mingw(os.getcwd())

    c = '''docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {docker_repo} '''.format(
        **locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def build(verbose):
    """Builds the docker image"""
    docker_build(verbose)


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def deploy(verbose):
    """Deploy the docker image to the Numer.ai compute node"""
    docker_build(verbose)

    docker_repo = read_docker_repo_file()

    keys = load_or_setup_keys()

    ecr_client = boto3.client('ecr', region_name='us-east-1',
                              aws_access_key_id=keys.aws_public, aws_secret_access_key=keys.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']).decode().split(':')

    if verbose:
        click.echo('running: docker login')
    res = subprocess.run(
        '''docker login -u {username} -p {password} {docker_repo}'''.format(**locals()), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res.check_returncode()

    c = '''docker push {docker_repo}'''.format(**locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


def main():
    init(autoreset=True)

    cli.add_command(setup)
    cli.add_command(destroy)

    cli.add_command(docker)
    cli()


if __name__ == "__main__":
    main()
