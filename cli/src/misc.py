from cli.src.constants import *
from cli.src.util.files import copy_files


@click.command()
@click.option(
    '--example', '-e', type=str, default=DEFAULT_EXAMPLE,
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
    if example not in EXAMPLES:
        click.secho(f'Invalid example, options are {EXAMPLES}', fg='red')
        return

    example_dir = os.path.join(EXAMPLE_PATH, example)
    dst_dir = dest if dest is not None else example
    click.echo(f'Copying {example} example to {dst_dir}')
    copy_files(example_dir, dst_dir, force=False, verbose=verbose)

    dockerignore_path = os.path.join(dst_dir, '.dockerignore')
    if not os.path.exists(dockerignore_path):
        with open(dockerignore_path, 'a+') as f:
            f.write(".numerai\n")
            f.write("numerai_dataset*\n")
            f.write(".git\n")
            f.write("venv\n")