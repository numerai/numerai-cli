from configparser import ConfigParser, MissingSectionHeaderError
import json

from cli.src.constants import *
from cli.src.util.debug import confirm
from cli.src.util.docker import terraform
from cli.src.util.files import \
    maybe_create,\
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
        maybe_create(temp_key_path)
        click.secho(f"\tmoving '{old_key_path}' to '{temp_key_path}'",)
        os.rename(old_key_path, temp_key_path)

    # MOVE CONFIG FILE
    if os.path.exists(old_config_path):
        click.secho(f"\tmoving {old_config_path} to {CONFIG_PATH}",)
        os.rename(old_config_path, CONFIG_PATH)

    # Double check keys file exists
    if not os.path.exists(KEYS_PATH):
        click.secho(f"No key file at {KEYS_PATH}, you must re-initialize them:")
        config_numerai_keys()
        config_provider_keys(PROVIDER_AWS)

    # REFORMAT OLD KEYS
    try:
        config = ConfigParser()
        config.read(KEYS_PATH)
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
        with open(os.open(KEYS_PATH, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as f:
            config.write(f)
            json.dump(new_config, f, indent=2)

    # if this file is already a json file skip
    except MissingSectionHeaderError:
        pass

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

    # RENAME AND UPDATE TERRAFORM FILES
    click.secho('Upgrading terraform files...', fg='yellow')
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
    terraform("init -upgrade", CONFIG_PATH, verbose=verbose)

    if confirm("It's recommended you destroy your current Compute Node. Continue?"):
        click.secho("Removing old cloud infrastructure...", fg='yellow')
        terraform(
            'destroy -auto-approve -var="node_config_file=nodes.json"',
            CONFIG_PATH, verbose, env_vars=load_or_init_keys('aws'),
        )

    click.secho('Upgrade complete!', fg='green')
    click.secho('run "numerai node create" to register this directory')
