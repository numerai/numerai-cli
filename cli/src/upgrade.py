import json

from cli.src.constants import *
from cli.src.util.debug import confirm
from cli.src.util.docker import terraform
from cli.src.util.files import \
    copy_files
from cli.src.util.keys import \
    load_or_init_keys, \
    config_numerai_keys, \
    config_provider_keys


@click.command()
@click.option('--verbose', '-v', is_flag=True)
def upgrade(verbose):
    """
    Upgrades configuration from <=0.2 format to >=0.3 format
    """
    home = str(Path.home())
    old_key_path = os.path.join(home, '.numerai')
    old_config_path = os.path.join(os.getcwd(), '.numerai/')

    if str(old_key_path) == str(old_config_path):
        click.secho('You cannot run this command from your home directory.')
        return

    if not os.path.exists(old_config_path):
        click.secho(
            'Run this command from the directory in which you first ran '
            '"numerai setup" (it should have the .numerai folder in it)'
        )
        return

    click.secho(f"Upgrading, do not interrupt or else "
                f"your environment may be corrupted.", fg='yellow')
    # MOVE KEYS FILE
    if os.path.isfile(old_key_path):
        temp_key_path = os.path.join(old_config_path, '.keys')
        click.secho(f"\tmoving '{old_key_path}' to '{temp_key_path}'",)
        os.rename(old_key_path, temp_key_path)

    # MOVE CONFIG FILE
    if os.path.exists(old_config_path):
        click.secho(f"\tmoving {old_config_path} to {CONFIG_PATH}",)
        os.rename(old_config_path, CONFIG_PATH)

    # Double check keys file exists
    keys_config = load_or_init_keys()
    if not os.path.exists(KEYS_PATH) or 'aws' not in keys_config or 'numerai' not in keys_config:
        click.secho(f"Keys missing from {KEYS_PATH}, you must re-initialize your keys:")
        config_numerai_keys()
        config_provider_keys(PROVIDER_AWS)

    # DELETE OLD CONFIG FILES
    click.secho('Checking for old config output files...', fg='yellow')
    old_suburl_path = os.path.join(CONFIG_PATH, 'submission_url.txt')
    if os.path.exists(old_suburl_path):
        click.secho(f"\tdeleting {old_suburl_path}, you can create the "
                    f"new config file with 'numerai node create'")
        os.remove(old_suburl_path)
    old_docker_path = os.path.join(CONFIG_PATH, 'docker_repo.txt')
    if os.path.exists(old_docker_path):
        click.secho(f"\tdeleting {old_docker_path}, you can create the "
                    f"new config file with 'numerai node create'")
        os.remove(old_docker_path)

    # UPGRADE, RENAME, AND UPDATE TERRAFORM FILES
    click.secho('Upgrading terraform files...', fg='yellow')
    try:
        with open(os.path.join(CONFIG_PATH, 'terraform.tfstate')) as f:
            tfstate = json.load(f)
        if '0.12' in tfstate['terraform_version']:
            terraform('0.13upgrade -yes', verbose, version='0.13.6')
            terraform('init', verbose, version='0.13.6')
            terraform('apply -auto-approve', verbose, version='0.13.6')
    except FileNotFoundError:
        pass
    except click.ClickException:
        click.secho("Failed to upgrade to terraform state!", fg='red')
        return

    tf_files_map = {
        'main.tf': '-main.tf',
        'variables.tf': '-inputs.tf',
        'outputs.tf': '-outputs.tf'
    }
    for old_file, new_file in tf_files_map.items():
        old_file = os.path.join(CONFIG_PATH, old_file)
        new_file = os.path.join(CONFIG_PATH, new_file)
        if not os.path.exists(old_file):
            continue
        click.secho(f'\trenaming {old_file} to {new_file} to prep for upgrade...')
        os.rename(old_file, new_file)
    copy_files(
        TERRAFORM_PATH,
        CONFIG_PATH,
        force=True,
        verbose=verbose
    )

    # terraform init
    click.secho("Re-initializing terraform...", fg='yellow')
    terraform("init -upgrade", verbose=verbose)

    if confirm("It's recommended you destroy your current Compute Node. Continue?"):
        click.secho("Removing old cloud infrastructure...", fg='yellow')
        terraform('destroy -auto-approve -var="node_config_file=nodes.json"', verbose,
                  env_vars=load_or_init_keys('aws'))

    click.secho('Upgrade complete!', fg='green')
    click.secho('run "numerai node create --help" to learn how to '
                'register this directory as a prediction node')
