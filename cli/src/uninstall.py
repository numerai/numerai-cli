import subprocess
import shutil

from cli.src.constants import *
from cli.src.util.debug import confirm
from cli.src.util.files import load_or_init_keys
from cli.src.util.docker import terraform


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
    if not confirm('Are you absolutely sure you want to uninstall?'):
        return

    if os.path.exists(CONFIG_PATH):
        all_keys = load_or_init_keys()
        provider_keys = {}
        for provider in PROVIDERS:
            provider_keys.update(all_keys[provider])
        terraform('destroy -auto-approve -var="node_config_file=nodes.json"',
                  CONFIG_PATH, verbose=True, env_vars=provider_keys)
        subprocess.run('docker system prune -f -a --volumes', shell=True)
        shutil.rmtree(CONFIG_PATH)
    try:
        subprocess.run('pip3 uninstall numerai-cli -y', shell=True)
    except PermissionError as e:
        click.secho('uninstall failed due to permissions, '
                    'run "pip3 uninstall numerai-cli -y" manually', fg='red')
    click.secho("All those moments will be lost in time, like tears in rain.", fg='red')
