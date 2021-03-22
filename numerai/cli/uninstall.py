import subprocess
import shutil

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.util.keys import \
    load_or_init_keys, \
    load_or_init_nodes, \
    get_numerai_keys
from numerai.cli.util.docker import terraform


@click.command()
def uninstall():
    """
    Completely removes everything created by numerai-cli and uninstall the package.
    """
    click.secho(
    '''DANGER WILL ROBINSON, This will:
    - Destroy all nodes in the cloud
    - Remove all docker images on your computer
    - Delete the .numerai configuration directory on your computer
    - Uninstall the numerai-cli python package
    - Leave Python and Docker installed on your computer
    ''', fg='red'
    )
    if not click.confirm('Are you absolutely sure you want to uninstall?'):
        return

    if os.path.exists(CONFIG_PATH):
        napi = base_api.Api(*get_numerai_keys())

        node_config = load_or_init_nodes()
        click.secho('deregistering all webhooks...')
        for node, config in node_config.items():
            napi.set_submission_webhook(config['model_id'], None)

        click.secho('destroying cloud resources...')
        all_keys = load_or_init_keys()
        provider_keys = {}
        for provider in PROVIDERS:
            if provider in all_keys.keys():
                provider_keys.update(all_keys[provider])
        terraform('destroy -auto-approve',
                  verbose=True, env_vars=provider_keys,
                  inputs={'node_config_file': 'nodes.json'})

        click.secho('cleaning up docker images...')
        subprocess.run('docker system prune -f -a --volumes', shell=True)
        shutil.rmtree(CONFIG_PATH)

    click.secho('uninstalling python package...')
    res = subprocess.run(
        'pip3 uninstall numerai-cli -y',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )

    if res.returncode != 0:
        if b'PermissionError' in res.stderr:
            click.secho(
                'uninstall failed due to permissions, '
                'run "pip3 uninstall numerai-cli -y" manually'
                'to ensure the package was uninstalled',
                fg='red'
            )
        else:
            click.secho(f'Unexpected error occurred:\n{res.stderr}', fg='red')

    click.secho("All those moments will be lost in time, like tears in rain.", fg='red')
