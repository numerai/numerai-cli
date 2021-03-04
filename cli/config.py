import os
import json
from stat import S_IRGRP, S_IROTH
from pathlib import Path
from configparser import ConfigParser

import click

from cli.util import \
    copy_files, \
    get_config_dir, \
    get_package_dir, \
    format_path_if_mingw, \
    run_terraform_cmd
from cli.doctor import \
    check_aws_validity, \
    check_numerai_validity

PROVIDER_AWS = "aws"
PROVIDERS = [PROVIDER_AWS]

DEFAULT_NODE = "default"
DEFAULT_SETTINGS = {
    'provider': PROVIDER_AWS,
    'cpu': 2048,
    'memory': 16384,
    'path': "."
}

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


def maybe_create(path):
    created = False

    directory = os.path.dirname(path)
    print(directory)
    if not os.path.exists(directory):
        print('creating...')
        os.makedirs(directory)

    if not os.path.exists(path):
        created = True
        with open(path, 'w+') as f:
            f.write('')

    return created


def get_config_path():
    return os.path.join(str(Path.home()), '.numerai/')


def get_key_file_path(create=True):
    path = os.path.join(get_config_path(), '.keys')
    if create:
        maybe_create(path)
    return path


def get_config_file_path(create=True):
    path = os.path.join(get_config_path(), 'nodes.json')
    if create:
        maybe_create(path)
    return path


class Config:

    def __init__(self):
        super().__init__()

        self._config_file_path = get_config_file_path()
        if os.stat(self._config_file_path).st_size == 0:
            self.nodes_config = {}
        else:
            self.nodes_config = json.load(open(self._config_file_path))

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
        check_numerai_validity(numerai_public, numerai_private)
        self.keys_config['numerai']['NUMERAI_PUBLIC_ID'] = numerai_public
        self.keys_config['numerai']['NUMERAI_SECRET_KEY'] = numerai_private
        self.write_keys()

    def configure_keys_aws(self, aws_public, aws_private):
        check_aws_validity(aws_public, aws_private)
        self.keys_config['aws']['AWS_ACCESS_KEY_ID'] = aws_public
        self.keys_config['aws']['AWS_SECRET_ACCESS_KEY'] = aws_private
        self.write_keys()

    def write_nodes(self):
        json.dump(self.nodes_config, open(self._config_file_path, 'w+'), indent=2)

    def configure_node(self, node, provider, cpu, memory, path):
        self.nodes_config.setdefault(node, {})
        self.nodes_config[node].update({
            key: default
            for key, default in DEFAULT_SETTINGS.items()
            if key not in self.nodes_config[node]
        })

        if provider:
            self.nodes_config[node]['provider'] = provider
        if cpu:
            self.nodes_config[node]['cpu'] = cpu
        if memory:
            self.nodes_config[node]['memory'] = memory
        if path:
            self.nodes_config[node]['path'] = path

        self.write_nodes()

    def delete_node(self, node):
        del self.nodes_config[node]
        self.write_nodes()

    def configure_outputs(self, outputs):
        for node, data in outputs.items():
            self.nodes_config[node].update(data)
        self.write_nodes()
        click.secho(f'wrote node configuration to: {self._config_file_path}', fg='yellow')

    def provider(self, node):
        return self.nodes_config[node]['provider']

    def path(self, node):
        return self.nodes_config[node]['path']

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
        return self.nodes_config[node]['docker_repo']

    def webhook_url(self, node):
        return self.nodes_config[node]['webhook_url']

    def cluster_log_group(self, node):
        return self.nodes_config[node]['cluster_log_group']

    def webhook_log_group(self, node):
        return self.nodes_config[node]['webhook_log_group']

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
    click.secho(f"Please type in the following keys "
                f"(press enter to keep the value in the brackets):", fg='yellow')

    if provider == PROVIDER_AWS:
        try:
            aws_public = config.aws_public
            aws_secret = config.aws_secret
        except KeyError:
            aws_public = None
            aws_secret = None
        config.configure_keys_aws(
            click.prompt(f'AWS_ACCESS_KEY_ID', default=aws_public).strip(),
            click.prompt(f'AWS_SECRET_ACCESS_KEY', default=aws_secret).strip()
        )

    try:
        numerai_public = config.numerai_public
        numerai_secret = config.numerai_secret
    except KeyError:
        numerai_public = None
        numerai_secret = None

    config.configure_keys_numerai(
        click.prompt(f'NUMERAI_PUBLIC_ID', default=numerai_public).strip(),
        click.prompt(f'NUMERAI_SECRET_KEY', default=numerai_secret).strip()
    )

    return config


def load_or_configure_node(provider):
    key_file = get_key_file_path()

    if not os.path.exists(key_file):
        click.echo("Key file not found at: " + key_file)
        return keys(provider)

    # Check permission and prompt to fix
    elif os.stat(key_file).st_mode & (S_IRGRP | S_IROTH):
        click.secho(f"WARNING: {key_file} is readable by others", fg='red')
        if click.confirm('Fix permissions?', default=True, show_default=True):
            os.chmod(key_file, 0o600)

    return Config()


@config.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--node', '-n', type=str, default=DEFAULT_NODE,
    help=f"Target a node. Defaults to '{DEFAULT_NODE}'.")
@click.option(
    '--provider', '-P', type=str,
    help=f"Select a cloud provider. One of {PROVIDERS}. Defaults to {DEFAULT_SETTINGS['provider']}.")
@click.option(
    '--cpu', '-c', type=int,
    help=f"Amount of CPU credits (cores * 1024) to use in the compute container (defaults to {DEFAULT_SETTINGS['cpu']}). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings")
@click.option(
    '--memory', '-m', type=int,
    help=f"Amount of Memory (in MiB) to use in the compute container (defaults to {DEFAULT_SETTINGS['memory']}). \
    \n See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings")
@click.option(
    '--path', '-p', type=str,
    help=f"Target a file path. Defaults to '{DEFAULT_SETTINGS['path']}' (current directory).")
def node(verbose, node, provider, cpu, memory, path):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """

    numerai_dir = format_path_if_mingw(get_config_dir())

    config = load_or_configure_node(provider)
    config.configure_node(node, provider, cpu, memory, path)

    # terraform init
    run_terraform_cmd("init -upgrade", config, numerai_dir, verbose)
    click.echo('succesfully setup .numerai with terraform')

    # terraform apply
    run_terraform_cmd(
        f'apply -auto-approve -var="node_config_file=nodes.json"',
        config, numerai_dir, verbose, env_vars=config.provider_keys(node))
    click.echo('successfully created cloud resources')

    # terraform output for AWS nodes
    click.echo('saving node configuration')
    aws_nodes = json.loads(run_terraform_cmd(
        f"output -json aws_nodes", config, numerai_dir, verbose, pipe_output=False
    ).stdout.decode('utf-8'))
    config.configure_outputs(aws_nodes)


@config.command()
# this is necessary for legacy code to be converted to newer formats
def upgrade():
    click.secho(f"Upgrading, do not interrupt or else "
                f"your environment may be corrupted.", fg='yellow')
    home = str(Path.home())
    old_key_path = os.path.join(home, '.numerai')
    old_config_path = os.path.join(os.getcwd(), '.numerai/')

    # MOVE KEYS FILE
    if os.path.isfile(old_key_path):
        temp_key_path = os.path.join(old_config_path, '.keys')
        maybe_create(temp_key_path)
        click.secho(f"Moving '{old_key_path}' to '{temp_key_path}'", fg='yellow')
        os.rename(old_key_path, temp_key_path)

    # MOVE CONFIG FILE
    new_config_path = get_config_path()
    if os.path.exists(old_config_path):
        click.secho(f"moving {old_config_path} to {new_config_path}", fg='yellow')
        os.rename(old_config_path, new_config_path)

    # REFORMAT OLD KEYS
    new_key_path = get_key_file_path()
    config = ConfigParser()
    config.read(new_key_path)
    if 'default' in config:
        click.secho(f"Old keyfile format found, reformatting...", fg='yellow')
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
        config.write(open(os.open(new_key_path, os.O_CREAT | os.O_WRONLY, 0o600), 'w'))

    # DELETE OLD CONFIG FILES
    old_suburl_path = os.path.join(new_config_path, 'submission_url.txt')
    if os.path.exists(old_suburl_path):
        click.secho(f"deleting {old_suburl_path}, you can create the "
                    f"new config file with 'numerai config node'", fg='yellow')
        os.remove(old_suburl_path)
    old_docker_path = os.path.join(new_config_path, 'docker_repo.txt')
    if os.path.exists(old_docker_path):
        click.secho(f"deleting {old_docker_path}, you can create the "
                    f"new config file with 'numerai config node'", fg='yellow')
        os.remove(old_docker_path)

    # RENAME AND UPDATE TERRAFORM FILES
    tf_files_map = {
        'main.tf': '-main.tf',
        'variables.tf': '-inputs.tf',
        'outputs.tf': '-outputs.tf'
    }
    for old_file, new_file in tf_files_map.items():
        old_file = os.path.join(new_config_path, old_file)
        new_file = os.path.join(new_config_path, new_file)
        if not os.path.exists(old_file):
            continue
        click.secho(f'renaming {old_file} to {new_file} to prep for upgrade...')
        os.rename(old_file, new_file)

    click.secho('upgrading terraform files...')
    copy_files(
        os.path.join(get_package_dir(), "terraform"),
        new_config_path,
        force=True,
        verbose=True
    )
