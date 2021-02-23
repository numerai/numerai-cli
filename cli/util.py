import os
import sys
import subprocess
import shutil

import click

from cli.doctor import root_cause


def run_terraform_cmd(tf_cmd, config, numerai_dir, verbose, pipe_output=True, env_vars=None):
    cmd = f"docker run"
    if env_vars:
        for key, val in env_vars.items():
            cmd += f' -e "{key}={val}"'
    cmd += f' --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:0.14.3 {tf_cmd}'

    if verbose:
        click.echo('Running: ' + config.sanitize_message(cmd))
    res = subprocess.run(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if res.stdout:
        click.echo(res.stdout.decode('utf8'))
    if res.stderr:
        click.secho(res.stderr.decode('utf8'), fg='red', file=sys.stderr)
    if res.returncode != 0:
        root_cause(res.stderr)
    res.check_returncode()

    return res


def copy_files(src, dst, force, verbose):
    if not os.path.exists(dst):
        os.mkdir(dst)
    for filename in os.listdir(src):
        src_file = os.path.join(src, filename)
        dst_file = os.path.join(dst, filename)
        if os.path.exists(dst_file) and not force:
            overwrite = click.prompt(f'{filename} already exists. Overwrite? [y]/n').strip()
            if overwrite != "" and overwrite != "y" and overwrite != "yes":
                return
        if os.path.isdir(src_file):
            if verbose:
                click.secho(f"copying directory {dst_file}", fg='yellow')
            os.makedirs(dst_file, exist_ok=True)
            copy_files(src_file, dst_file, force, verbose)
        else:
            if verbose:
                click.secho(f"copying file {dst_file}", fg='yellow')
            shutil.copy(src_file, dst_file)


def get_project_numerai_dir():
    return os.path.join(os.getcwd(), ".numerai")


def get_code_dir():
    return os.path.dirname(__file__)


def format_path_if_mingw(p):
    '''
    Helper function to format if the system is running docker toolbox + mingw.
    The paths need to be formatted like unix paths, and the drive letter needs to be lowercased
    '''
    if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ and 'MSYSTEM' in os.environ:
        p = '/' + p[0].lower() + p[2:]
        p = p.replace('\\', '/')
    return p