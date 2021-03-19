import click

from numerai.cli.constants import *
from numerai.cli.util import files


@click.command()
@click.option(
    '--example', '-e', type=click.Choice(EXAMPLES), default=DEFAULT_EXAMPLE,
    help=f'Specify the example to copy, defaults to {DEFAULT_EXAMPLE}. '
         f'Options are {EXAMPLES}.'
)
@click.option(
    '--dest', '-d', type=str,
    help=f'Destination folder to which example code is written. '
         f'Defaults to the name of the example.'
)
@click.option('--verbose', '-v', is_flag=True)
def copy_example(example, dest, verbose):
    """
    Copies all example files into the current directory.

    WARNING: this will overwrite the following files if they exist:

        - Python: Dockerfile, model.py, train.py, predict.py, and requirements.txt

        - RLang:  Dockerfile, install_packages.R, main.R
    """
    files.copy_example(example, dest, verbose)


@click.command()
def list_constants():
    """
    Default and constant values used by the CLI
    """
    click.secho(f'''
    
    ---Tournament Numbers---
    TOURNAMENT_NUMERAI: {TOURNAMENT_NUMERAI}
    TOURNAMENT_SIGNALS: {TOURNAMENT_SIGNALS}

    ---Paths---
    PACKAGE_PATH: {PACKAGE_PATH}
    CONFIG_PATH: {CONFIG_PATH}
    KEYS_PATH: {KEYS_PATH}
    NODES_PATH: {NODES_PATH}
    TERRAFORM_PATH: {TERRAFORM_PATH}
    EXAMPLE_PATH: {EXAMPLE_PATH}

    ---Cloud Interaction---
    PROVIDERS: {PROVIDERS}
    LOG_TYPES: {LOG_TYPES}

    ---Prediction Nodes---
    DEFAULT_EXAMPLE: {DEFAULT_EXAMPLE}
    DEFAULT_SIZE: {DEFAULT_SIZE}
    DEFAULT_PROVIDER: {DEFAULT_PROVIDER}
    DEFAULT_PATH: {DEFAULT_PATH}
    DEFAULT_SETTINGS: {json.dumps(DEFAULT_SETTINGS, indent=2)}
    SIZE_PRESETS:
    ''')
    for size, preset in SIZE_PRESETS.items():
        suffix = '(default)' if size == DEFAULT_SIZE else ''
        click.secho(
            f'\t{size} -> cpus: {preset[0] / 1024}, '
            f'mem: {preset[1] / 1024} GB {suffix}',
            fg='green' if size == DEFAULT_SIZE else 'yellow'
        )
    click.secho(
        "See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html "
        "for more info about size presets.")