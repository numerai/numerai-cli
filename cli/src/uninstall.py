import subprocess
import shutil

from cli.src.constants import *
from cli.src.util.keys import get_provider_keys
from cli.src.util.files import load_or_init_nodes
from cli.src.util.docker import terraform, cleanup


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
    confirm = click.prompt('Are you absolutely sure you want to uninstall? [y]/n').strip()
    if confirm != "" and confirm != "y" and confirm != "yes":
        return

    if os.path.exists(CONFIG_PATH):
        node_config = load_or_init_nodes()
        all_provider_keys = {}
        for n in node_config.keys():
            all_provider_keys.update(get_provider_keys(n))
        terraform('destroy -auto-approve  -var="node_config_file=nodes.json"',
                  CONFIG_PATH, verbose=True, env_vars=all_provider_keys)
        subprocess.run('docker system prune -f -a --volumes', shell=True)
        shutil.rmtree(CONFIG_PATH)

    subprocess.run('pip3 uninstall numerai-cli -y', shell=True)
    click.secho("All those moments will be lost in time, like tears in rain.", fg='red')
