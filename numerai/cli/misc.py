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
