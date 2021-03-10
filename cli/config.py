import os
import json
from stat import S_IRGRP, S_IROTH
from pathlib import Path
from configparser import ConfigParser, MissingSectionHeaderError

import click
import numerapi

from cli.util import \
    copy_files, \
    get_package_dir, \
    format_path_if_mingw, \
    run_terraform_cmd, \
    check_aws_validity, \
    check_numerai_validity

PROVIDER_AWS = "aws"
PROVIDER_GCP = "gcp"
PROVIDERS = [
    PROVIDER_AWS,
    # PROVIDER_GCP
]

SIZE_PRESETS = {
    "gen-sm": (1024, 4096),
    "gen-md": (2048, 8192),
    "gen-lg": (4096, 16384),
    "gen-xl": (8192, 30720),

    "cpu-sm": (1024, 2048),
    "cpu-md": (2048, 4096),
    "cpu-lg": (4096, 8192),
    "cpu-xl": (8192, 16384),

    "mem-sm": (1024, 8192),
    "mem-md": (2048, 16384),
    "mem-lg": (4096, 30720),
}

DEFAULT_NODE = "default"
DEFAULT_SIZE = "gen-md"
DEFAULT_SETTINGS = {
    'provider': PROVIDER_AWS,
    'cpu': SIZE_PRESETS[DEFAULT_SIZE][0],
    'memory': SIZE_PRESETS[DEFAULT_SIZE][1],
    'path': os.getcwd()
}


def maybe_create(path, protected=False):
    created = False

    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(path):
        created = True
        if protected:
            with open(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as f:
                f.write('')
        else:
            with open(path, 'w+') as f:
                f.write('')

    return created


def get_config_path():
    return os.path.join(str(Path.home()), '.numerai/')


def get_key_file_path():
    path = os.path.join(get_config_path(), '.keys')
    created = maybe_create(path, protected=True)
    # Check permission and prompt to fix
    if os.stat(path).st_mode & (S_IRGRP | S_IROTH):
        click.secho(f"WARNING: {path} is readable by others", fg='red')
        if click.confirm('Fix permissions?', default=True, show_default=True):
            os.chmod(path, 0o600)
    return path, created


def get_node_file_path():
    path = os.path.join(get_config_path(), 'nodes.json')
    maybe_create(path)
    return path


def load_config_file(file_path):
    if os.stat(file_path).st_size == 0:
        return {}
    with open(file_path) as f:
        return json.load(f)


class Config:

    def __init__(self):
        super().__init__()

        self._config_file_path = get_node_file_path()
        self.nodes_config = load_config_file(self._config_file_path)

        self._keyfile_path, self.keyfile_is_new = get_key_file_path()
        self.keys_config = load_config_file(self._keyfile_path)

    def write_keys(self):
        with open(self._keyfile_path, 'w') as configfile:
            json.dump(self.keys_config, configfile, indent=2)

    def configure_aws(self):
        aws_public, aws_secret = self.aws_keys
        aws_public = click.prompt(f'AWS_ACCESS_KEY_ID', default=aws_public).strip()
        aws_secret = click.prompt(f'AWS_SECRET_ACCESS_KEY', default=aws_secret).strip()
        check_aws_validity(aws_public, aws_secret)
        self.keys_config.setdefault('aws', {})
        self.keys_config['aws']['AWS_ACCESS_KEY_ID'] = aws_public
        self.keys_config['aws']['AWS_SECRET_ACCESS_KEY'] = aws_secret
        self.write_keys()

    # TODO: GCP support
    # def configure_gcp(self):
    #     gcp_keys = {
    #         'test': 'test'
    #     }
    #     gcp_path = click.prompt(f'GCP Key File Path', default=gcp_keys).strip()
    #     print(gcp_path)
    #     try:
    #         with open(gcp_path, 'r') as f:
    #             gcp_keys = json.load(f)
    #     except FileNotFoundError:
    #         click.secho(f'file {gcp_path} does not exist', color='red')
    #         exit()
    #     print(gcp_keys)
    #     self.keys_config['gcp'] = gcp_keys
    #     self.write_keys()

    def configure_provider_keys(self, cloud_provider):
        click.secho(f"Setting up key file at {self._keyfile_path}\n", fg='yellow')
        click.secho(f"Please type in the following keys "
                    f"(press enter to keep the value in the brackets):",
                    fg='yellow')

        if cloud_provider == PROVIDER_AWS:
            self.configure_aws()

    def configure_numerai_keys(self):
        numerai_public, numerai_secret = self.numerai_keys
        numerai_public = click.prompt(f'NUMERAI_PUBLIC_ID', default=numerai_public).strip()
        numerai_secret = click.prompt(f'NUMERAI_SECRET_KEY', default=numerai_secret).strip()
        check_numerai_validity(numerai_public, numerai_secret)
        self.keys_config.setdefault('numerai', {})
        self.keys_config['numerai']['NUMERAI_PUBLIC_ID'] = numerai_public
        self.keys_config['numerai']['NUMERAI_SECRET_KEY'] = numerai_secret
        self.write_keys()

    def write_nodes(self):
        json.dump(self.nodes_config, open(self._config_file_path, 'w+'), indent=2)

    def configure_node(self, node, provider, size, path):
        self.nodes_config.setdefault(node, {})
        self.nodes_config[node].update({
            key: default
            for key, default in DEFAULT_SETTINGS.items()
            if key not in self.nodes_config[node]
        })

        if provider:
            self.nodes_config[node]['provider'] = provider
        if size:
            self.nodes_config[node]['cpu'] = SIZE_PRESETS[size][0]
            self.nodes_config[node]['memory'] = SIZE_PRESETS[size][1]
        if path:
            self.nodes_config[node]['path'] = os.path.abspath(path)

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

    def provider_keys(self, node):
        return self.keys_config[self.provider(node)]

    @property
    def aws_keys(self):
        try:
            return self.keys_config['aws']['AWS_ACCESS_KEY_ID'],\
                   self.keys_config['aws']['AWS_SECRET_ACCESS_KEY']
        except KeyError:
            return None, None

    @property
    def gcp_keys(self):
        try:
            return self.keys_config['gcp']
        except KeyError:
            return None, None

    @property
    def numerai_keys(self):
        try:
            return self.numerai_keys_dict['NUMERAI_PUBLIC_ID'],\
                   self.numerai_keys_dict['NUMERAI_SECRET_KEY']
        except KeyError:
            return None, None

    @property
    def numerai_keys_dict(self):
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
        aws_public, aws_secret = self.aws_keys
        numerai_public, numerai_secret = self.numerai_keys
        return message.replace(aws_public, '...')\
                      .replace(aws_secret, '...')\
                      .replace(numerai_public, '...')\
                      .replace(numerai_secret, '...')


@click.group()
def config():
    """Docker commands for building/deploying an image."""
    pass


@config.command()
@click.option(
    '--provider', '-p', type=str, default=PROVIDER_AWS,
    help=f"Select a cloud provider. One of {PROVIDERS}. "
         f"Defaults to {DEFAULT_SETTINGS['provider']}.")
def keys(provider):
    """Write API keys to configuration file."""
    config = Config()
    config.configure_provider_keys(provider)
    config.configure_numerai_keys()


@config.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--node', '-n', type=str, default=DEFAULT_NODE,
    help=f"Target a node. Defaults to '{DEFAULT_NODE}'.")
@click.option(
    '--provider', '-P', type=str,
    help=f"Select a cloud provider. One of {PROVIDERS}. "
         f"Defaults to {DEFAULT_SETTINGS['provider']}.")
@click.option(
    '--size', '-s', type=str,
    help=f"Combination of CPU credits (cores * 1024) and Memory (in MiB) to use in the compute container "
         f"One of {json.dumps(SIZE_PRESETS, indent=2)}.\n(defaults to {DEFAULT_SIZE})."
         f"\nSee https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for more info")
@click.option(
    '--path', '-p', type=str,
    help=f"Target a file path. Defaults to '{DEFAULT_SETTINGS['path']}'.")
@click.option(
    '--model-id', '-i', type=str,
    help=f"Target a model to configure this node for.")
def node(verbose, node, provider, size, path, model_id):
    """
    Uses Terraform to create a full Numerai Compute cluster in AWS.
    Prompts for your AWS and Numerai API keys on first run, caches them in $HOME/.numerai.

    At the end of running, this will output a config file 'nodes.json'.
    """
    click.secho(f'Configuring node {node}')

    # check if they have keys configured, configure them if not
    config = Config()

    if config.keyfile_is_new:
        config.configure_numerai_keys()

    if provider and provider not in config.keys_config:
        config.configure_provider_keys(provider)

    if path and not os.path.isdir(path):
        click.secho(f"could not find path {path}", fg='red')
        return
    config.configure_node(node, provider, size, path)

    numerai_dir = format_path_if_mingw(get_config_path())

    click.secho("running terraform to provision cloud infrastructure...")
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

    if model_id:
        napi = numerapi.NumerAPI(*config.numerai_keys)
        napi.raw_query(
            '''
            mutation (
                $modelId: String!
                $newSubmissionWebhook: String!
            ) {
                setSubmissionWebhook(
                    modelId: $modelId
                    newSubmissionWebhook: $newSubmissionWebhook
                )
            }
            ''',
            variables={
                'modelId': model_id,
                'newSubmissionWebhook': config.webhook_url(node)
            },
            authorization=True
        )


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
    new_key_path, _ = get_key_file_path()
    try:
        config = ConfigParser()
        config.read(new_key_path)
        click.secho(f"Old keyfile format found, reformatting...", fg='yellow')

        new_config = {
            'aws': {
                'AWS_ACCESS_KEY_ID': config['default']['AWS_ACCESS_KEY_ID'],
                'AWS_SECRET_ACCESS_KEY': config['default']['AWS_SECRET_ACCESS_KEY']
            },
            'numerai': {
                'NUMERAI_PUBLIC_ID': config['default']['NUMERAI_PUBLIC_ID'],
                'NUMERAI_SECRET_KEY': config['default']['NUMERAI_SECRET_KEY']
            }
        }

        del config['default']
        with open(os.open(new_key_path, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as f:
            config.write(f)
            json.dump(new_config, f, indent=2)

    # if this file is already a json file skip
    except MissingSectionHeaderError:
        pass

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

    # Update terraform files
    click.secho('upgrading terraform files...')
    copy_files(
        os.path.join(get_package_dir(), "terraform"),
        new_config_path,
        force=True,
        verbose=True
    )
