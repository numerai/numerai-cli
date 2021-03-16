import json
import shutil

from cli.src.constants import *
from cli.src.util.debug import confirm


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


def load_or_init_keys(provider=None):
    maybe_create(KEYS_PATH, protected=True)
    cfg = load_config(KEYS_PATH)
    if provider:
        return cfg[provider]
    return cfg


def load_or_init_nodes(node=None):
    maybe_create(NODES_PATH)
    cfg = load_config(NODES_PATH)
    if node:
        return cfg[node]
    return cfg


def copy_files(src, dst, force=False, verbose=True):
    if not os.path.exists(dst):
        os.mkdir(dst)
    for filename in os.listdir(src):
        src_file = os.path.join(src, filename)
        dst_file = os.path.join(dst, filename)
        if os.path.exists(dst_file) and not force:
            if not confirm(f'{filename} already exists. Overwrite?'):
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


def format_path_if_mingw(p):
    '''
    Helper function to format if the system is running docker toolbox + mingw.
    The paths need to be formatted like unix paths, and the drive letter needs to be lowercased
    '''
    if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ and 'MSYSTEM' in os.environ:
        p = '/' + p[0].lower() + p[2:]
        p = p.replace('\\', '/')
    return p
