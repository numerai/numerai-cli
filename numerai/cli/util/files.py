import json
import shutil

from numerai.cli.constants import *


def load_config(path):
    if os.stat(path).st_size == 0:
        return {}
    with open(path) as f:
        return json.load(f)


def store_config(path, obj):
    with open(path, 'w+') as f:
        json.dump(obj, f, indent=2)


def maybe_create(path, protected=False):
    created = False

    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not os.path.exists(path):
        created = True
        if protected:
            store_config(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600), {})
            os.chmod(path, 0o600)
        else:
            store_config(path, {})

    return created


def load_or_init_nodes(node=None):
    maybe_create(NODES_PATH)
    cfg = load_config(NODES_PATH)
    try:
        return cfg[node] if node else cfg
    except KeyError:
        click.secho(
            'Node has not been created, run `numerai node --help` '
            'to learn how to create one', fg='red'
        )
        exit(1)


def copy_files(src, dst, force=False, verbose=True):
    if not os.path.exists(dst):
        os.mkdir(dst)
    for filename in os.listdir(src):
        src_file = os.path.join(src, filename)
        dst_file = os.path.join(dst, filename)
        if os.path.exists(dst_file) and not force:
            if not click.confirm(f'{filename} already exists. Overwrite?'):
                return
        if os.path.isdir(src_file):
            if verbose:
                click.secho(f"copying directory {dst_file}", fg='yellow')
            os.makedirs(dst_file, exist_ok=True)
            copy_files(src_file, dst_file, force=force, verbose=verbose)
        else:
            if verbose:
                click.secho(f"copying file {dst_file}", fg='yellow')
            shutil.copy(src_file, dst_file)


def copy_example(example, dest, verbose):
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
