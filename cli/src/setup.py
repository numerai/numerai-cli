from cli.src.constants import *
from cli.src.util.docker import terraform
from cli.src.util.files import \
    maybe_create, \
    format_path_if_mingw, \
    copy_files
from cli.src.util.keys import \
    config_numerai_keys, \
    config_provider_keys


@click.command()
@click.option(
    '--provider', '-p', type=str, default=DEFAULT_PROVIDER,
    help=f"Initialize with this providers API keys. Defaults to {DEFAULT_PROVIDER}.")
@click.option('--verbose', '-v', is_flag=True)
def setup(provider, verbose):
    """
    Initializes configuration directory and provider API keys
    """
    # check for old format, tell user to run numerai upgrade first
    if os.path.isfile(CONFIG_PATH) or os.path.isdir('.numerai'):
        click.secho('It looks like you have an old configuration of numerai-cli,'
                    'run "numerai upgrade" first.')
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
    numerai_dir = format_path_if_mingw(CONFIG_PATH)
    copy_files(TERRAFORM_PATH, numerai_dir, verbose=True)

    # terraform init
    click.secho("initializing terraform to provision cloud infrastructure...")
    terraform("init -upgrade", verbose)

    click.secho("✓ Numerai API Keys setup and working", fg='green')
    click.secho(f"✓ {provider} API Keys setup and working", fg='green')
    click.secho(f"✓ Terraform files copied to {numerai_dir}", fg='green')
    click.echo('succesfully initialized numerai-cli')