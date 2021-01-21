import os
import json
from stat import S_IRGRP, S_IROTH
from pathlib import Path
from configparser import ConfigParser

import click

from cli.util import get_project_numerai_dir
from cli.doctor import \
    check_aws_validity, \
    check_numerai_validity

PROVIDER_AWS = "aws"

DEFAULT_PROVIDER = PROVIDER_AWS
DEFAULT_CPU = 1024
DEFAULT_MEMORY = 8192


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

    def configure_app(self, app, provider, cpu, memory):
        self.apps_config.setdefault(app, {})

        if 'PROVIDER' not in self.apps_config[app]:
            self.apps_config[app]['provider'] = DEFAULT_PROVIDER
        if provider:
            self.apps_config[app]['provider'] = provider

        if 'CPU' not in self.apps_config[app]:
            self.apps_config[app]['cpu'] = DEFAULT_CPU
        if cpu:
            self.apps_config[app]['cpu'] = cpu

        if 'MEMORY' not in self.apps_config[app]:
            self.apps_config[app]['memory'] = DEFAULT_MEMORY
        if memory:
            self.apps_config[app]['memory'] = memory

        self.write_apps()

    def delete_app(self, app):
        del self.apps_config[app]
        self.write_apps()

    def configure_outputs(self, outputs):
        for app, data in outputs.items():
            self.apps_config[app].update(data)
        self.write_apps()
        click.secho(f'wrote application urls (submission_url, docker_repo, etc.) to: {self._keyfile_path}', fg='yellow')

    def provider(self, app):
        return self.apps_config[app]['provider']

    @property
    def aws_public(self):
        return self.keys_config['aws']['AWS_ACCESS_KEY_ID']

    @property
    def aws_secret(self):
        return self.keys_config['aws']['AWS_SECRET_ACCESS_KEY']

    def provider_keys(self, app):
        return self.keys_config[self.provider(app)]

    @property
    def numerai_public(self):
        return self.keys_config['numerai']['NUMERAI_PUBLIC_ID']

    @property
    def numerai_secret(self):
        return self.keys_config['numerai']['NUMERAI_SECRET_KEY']

    @property
    def numerai_keys(self):
        return self.keys_config['numerai']

    def docker_repo(self, app):
        return self.apps_config[app]['docker_repo']

    def webhook_url(self, app):
        return self.apps_config[app]['webhook_url']

    def cluster_log_group(self, app):
        return self.apps_config[app]['cluster_log_group']

    def webhook_log_group(self, app):
        return self.apps_config[app]['webhook_log_group']

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



@click.command()
@click.option(
    '--provider', '-p', type=str, default=PROVIDER_AWS,
    help="Select a cloud provider. One of ['aws']. Defaults to 'aws'.")
def configure_keys(provider):
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