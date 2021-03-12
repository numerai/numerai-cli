from configparser import ConfigParser, MissingSectionHeaderError
import json

from cli.src.constants import *
from cli.src.util.files import \
    maybe_create,\
    copy_files


@click.command()
def upgrade():
    """
    Upgrades configuration from <=0.2 format to >=0.3 format
    """
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
    if os.path.exists(old_config_path):
        click.secho(f"moving {old_config_path} to {CONFIG_PATH}", fg='yellow')
        os.rename(old_config_path, CONFIG_PATH)

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
    old_suburl_path = os.path.join(CONFIG_PATH, 'submission_url.txt')
    if os.path.exists(old_suburl_path):
        click.secho(f"deleting {old_suburl_path}, you can create the "
                    f"new config file with 'numerai node create'", fg='yellow')
        os.remove(old_suburl_path)
    old_docker_path = os.path.join(CONFIG_PATH, 'docker_repo.txt')
    if os.path.exists(old_docker_path):
        click.secho(f"deleting {old_docker_path}, you can create the "
                    f"new config file with 'numerai node create'", fg='yellow')
        os.remove(old_docker_path)

    # RENAME AND UPDATE TERRAFORM FILES
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
        click.secho(f'renaming {old_file} to {new_file} to prep for upgrade...')
        os.rename(old_file, new_file)

    # Update terraform files
    click.secho('upgrading terraform files...')
    copy_files(
        TERRAFORM_PATH,
        CONFIG_PATH,
        force=True,
        verbose=True
    )
