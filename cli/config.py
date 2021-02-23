import os
import json
from stat import S_IRGRP, S_IROTH
from pathlib import Path
from configparser import ConfigParser

import click

from cli.util import \
    copy_files, \
    get_project_numerai_dir, \
    get_code_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.doctor import \
    check_aws_validity, \
    check_numerai_validity

PROVIDER_AWS = "aws"

DEFAULT_PROVIDER = PROVIDER_AWS
DEFAULT_CPU = 2048
DEFAULT_MEMORY = 16384

SIZE_PRESETS = {
    "gen-sm": (1024, 4096),
    "gen-md": (2, 8192),
    "gen-lg": (4, 16384),
    "gen-xl": (8, 32768),

    "cpu-sm": (1, 2048),
    "cpu-md": (2, 4096),
    "cpu-lg": (4, 8192),
    "cpu-xl": (8, 16384),

    "mem-sm": (1, 8192),
    "mem-md": (2, 16384),
    "mem-lg": (4, 32768),
    "mem-xl": (8, 65536),
}


def get_key_file_path():
    home = str(Path.home())

    old_path = os.path.join(home, '.numerai')
    keyfile_path = os.path.join(get_project_numerai_dir(), '.keys')

    # this is necessary for legacy code to be converted to new config format
    if os.path.exists(old_path):
        click.secho(f"Old version of keyfile found at '{old_path}', moving to new location {keyfile_path} ", fg='red')
        os.rename(old_path, keyfile_path)

    config = ConfigParser()
    config.read(keyfile_path)
    if 'default' in config:
        click.secho(f"reformatting...", fg='red')
        aws_access_key = config['default']['AWS_ACCESS_KEY_ID']
        aws_secret_key = config['default']['AWS_SECRET_ACCESS_KEY']
        numerai_public = config['default']['NUMERAI_PUBLIC_ID']
        numerai_secret = config['default']['NUMERAI_SECRET_KEY']
        config.optionxform = str
        config['aws'] = {}
        config['aws']['AWS_ACCESS_KEY_ID'] = aws_access_key
        config['aws']['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
        config['numerai'] = {}
        config['numerai']['NUMERAI_PUBLIC_ID'] = numerai_public
        config['numerai']['NUMERAI_SECRET_KEY'] = numerai_secret
        del config['default']
        config.write(open(os.open(keyfile_path, os.O_CREAT | os.O_WRONLY, 0o600), 'w'))

    return keyfile_path


def get_app_config_path():
    config_path = os.path.join(get_project_numerai_dir(), 'apps.json')
    created = False

    if not os.path.exists(config_path):
        created = True
        with open(config_path, 'w+') as f:
            json.dump({}, f)

    return config_path, created


class Config:

    def __init__(self):
        super().__init__()

        self._appconfig_path, _ = get_app_config_path()
        self.apps_config = json.load(open(self._appconfig_path))

        self._keyfile_path = get_key_file_path()
        self.keys_config = ConfigParser()
        self.keys_config.optionxform = str

        # load or create the file
        try:
            self.keys_config.read(self._keyfile_path)
        except FileNotFoundError:
            self.keys_config.write_keys()

    def write_keys(self):
        self.keys_config.optionxform = str
        with open(os.open(self._keyfile_path, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as configfile:
            self.keys_config.write(configfile)

    def configure_keys_numerai(self, numerai_public, numerai_private):
        self.keys_config['numerai']['NUMERAI_PUBLIC_ID'] = numerai_public
        self.keys_config['numerai']['NUMERAI_SECRET_KEY'] = numerai_private
        self.write_keys()

    def configure_keys_aws(self, aws_public, aws_private):
        self.keys_config['aws']['AWS_ACCESS_KEY_ID'] = aws_public
        self.keys_config['aws']['AWS_SECRET_ACCESS_KEY'] = aws_private
        self.write_keys()

    def write_apps(self):
        json.dump(self.apps_config, open(self._appconfig_path, 'w+'), indent=2)

    def configure_app(self, node, provider, cpu, memory):
        self.apps_config.setdefault(node, {})

        if 'PROVIDER' not in self.apps_config[node]:
            self.apps_config[node]['provider'] = DEFAULT_PROVIDER
        if provider:
            self.apps_config[node]['provider'] = provider

        if 'CPU' not in self.apps_config[node]:
            self.apps_config[node]['cpu'] = DEFAULT_CPU
        if cpu:
            self.apps_config[node]['cpu'] = cpu

        if 'MEMORY' not in self.apps_config[node]:
            self.apps_config[node]['memory'] = DEFAULT_MEMORY
        if memory:
            self.apps_config[node]['memory'] = memory

        self.write_apps()

    def delete_app(self, node):
        del self.apps_config[node]
        self.write_apps()

    def configure_outputs(self, outputs):
        for node, data in outputs.items():
            self.apps_config[node].update(data)
        self.write_apps()
        click.secho(f'wrote application urls (submission_url, docker_repo, etc.) to: {self._keyfile_path}', fg='yellow')

    def provider(self, node):
        return self.apps_config[node]['provider']

    @property
    def aws_public(self):
        return self.keys_config['aws']['AWS_ACCESS_KEY_ID']

    @property
    def aws_secret(self):
        return self.keys_config['aws']['AWS_SECRET_ACCESS_KEY']

    def provider_keys(self, node):
        return self.keys_config[self.provider(node)]

    @property
    def numerai_public(self):
        return self.keys_config['numerai']['NUMERAI_PUBLIC_ID']

    @property
    def numerai_secret(self):
        return self.keys_config['numerai']['NUMERAI_SECRET_KEY']

    @property
    def numerai_keys(self):
        return self.keys_config['numerai']

    def docker_repo(self, node):
        return self.apps_config[node]['docker_repo']

    def webhook_url(self, node):
        return self.apps_config[node]['webhook_url']

    def cluster_log_group(self, node):
        return self.apps_config[node]['cluster_log_group']

    def webhook_log_group(self, node):
        return self.apps_config[node]['webhook_log_group']

    def sanitize_message(self, message):
        return message.replace(
            self.aws_public, '...'
        ).replace(
            self.aws_secret, '...'
        ).replace(
            self.numerai_public, '...'
        ).replace(
            self.numerai_secret, '...'
        )


@click.group()
def config():
    """Docker commands for building/deploying an image."""
    pass


@config.command()
@click.option(
    '--provider', '-p', type=str, default=PROVIDER_AWS,
    help="Select a cloud provider. One of ['aws']. Defaults to 'aws'.")
def keys(provider):
    """Write API keys to configuration file."""
    config = Config()
    click.secho(f"Setting up key file at {config._keyfile_path}\n", fg='yellow')
    click.secho(f"Please type in the following keys:", fg='yellow')

    numerai_public = click.prompt('NUMERAI_PUBLIC_ID').strip()
    numerai_private = click.prompt('NUMERAI_SECRET_KEY').strip()
    check_numerai_validity(numerai_public, numerai_private)
    config.configure_keys_numerai(numerai_public, numerai_private)

    if provider == PROVIDER_AWS:
        aws_public = click.prompt('AWS_ACCESS_KEY_ID').strip()
        aws_private = click.prompt('AWS_SECRET_ACCESS_KEY').strip()
        check_aws_validity(aws_public, aws_private)
        config.configure_keys_aws(aws_public, aws_private)

    return config


def load_or_configure_app(provider):
    key_file = get_key_file_path()

    if not os.path.exists(key_file):
        click.echo("Key file not found at: " + get_key_file_path())
        return configure_keys(provider)

    # Check permission and prompt to fix
    elif os.stat(key_file).st_mode & (S_IRGRP | S_IROTH):
        click.secho(f"WARNING: {key_file} is readable by others", fg='red')
        if click.confirm('Fix permissions?', default=True, show_default=True):
            os.chmod(key_file, 0o600)

    return Config()


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
    '--node', '-n', type=str, default='default',
    help="Target a node. Defaults to 'default'.")
@click.option(
    '--update', '-u', is_flag=True,
    help="Update files in .numerai (terraform, lambda zips, and other copied files)")
def node(verbose, cpu, memory, provider, node, update):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    Will output two important URLs at the end of running:
        - submission_url:   The webhook url you will provide to Numerai.
                            A copy is stored in .numerai/submission_url.txt.

        - docker_repo:      Used for "numerai docker ..."
    """
    numerai_dir = get_project_numerai_dir()
    if not os.path.exists(numerai_dir) or update:
        copy_files(
            os.path.join(get_code_dir(), "terraform"),
            get_project_numerai_dir(),
            force=True,
            verbose=verbose
        )
    numerai_dir = format_path_if_mingw(numerai_dir)

    config = load_or_configure_app(provider)
    config.configure_app(node, provider, cpu, memory)

    # terraform init
    run_terraform_cmd("init -upgrade", config, numerai_dir, verbose)
    click.echo('succesfully setup .numerai with terraform')

    # terraform apply
    run_terraform_cmd(
        f'apply -auto-approve -var="app_config_file=apps.json"',
        config, numerai_dir, verbose, env_vars=config.provider_keys(node))
    click.echo('successfully created cloud resources')

    # terraform output for AWS apps
    click.echo('retrieving application configs')
    aws_applications = json.loads(run_terraform_cmd(
        f"output -json aws_applications", config, numerai_dir, verbose, pipe_output=False
    ).stdout.decode('utf-8'))
    config.configure_outputs(aws_applications)