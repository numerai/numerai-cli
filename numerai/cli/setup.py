import click

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform
from numerai.cli.util.files import \
    maybe_create, \
    copy_files
from numerai.cli.util.keys import \
    config_numerai_keys, \
    config_provider_keys


@click.command()
@click.option(
    '--provider', '-p', type=str, default=DEFAULT_PROVIDER,
    help=f"Initialize with this providers API keys. Defaults to {DEFAULT_PROVIDER}.")
@click.option('--verbose', '-v', is_flag=True)
def setup(provider, verbose):
    """
    Initializes cli and provider API keys.
    """
    # check for old format, tell user to run numerai upgrade first
    #if os.path.isfile(CONFIG_PATH) or os.path.isdir('.numerai'):
    #    click.secho('It looks like you have an old configuration of numerai-cli,'
    #                'run `numerai upgrade` first.')
    #    return
    
    if os.path.isdir(CONFIG_PATH) and not os.path.isdir(os.path.join(CONFIG_PATH,'azure')):
        click.secho('Looks like you have an old configuration of numerai-cli (<=0.3).'
                    'run `numerai upgrade` first.')
        return

    # setup numerai keys
    click.secho("Initializing numerai keys "
                "(press enter to keep value in brackets)...", fg='yellow')
    maybe_create(KEYS_PATH, protected=True)
    config_numerai_keys()

    # setup provider keys
    click.secho(f"\nInitializing {provider} keys "
                f"(press enter to keep value in brackets)...", fg='yellow')
    config_provider_keys(provider)

    # copy tf files
    click.secho("copying terraform files...")
    copy_files(TERRAFORM_PATH, CONFIG_PATH, force=True, verbose=True)

    # terraform init, added provider to init at the specified provider's tf directory
    click.secho("initializing terraform to provision cloud infrastructure...")
    terraform("init -upgrade ", verbose, provider)

    click.secho("Numerai API Keys setup and working", fg='green')
    click.secho(f"{provider} API Keys setup and working", fg='green')
    click.secho(f"Terraform files copied to {CONFIG_PATH}", fg='green')
    click.echo('succesfully initialized numerai-cli')