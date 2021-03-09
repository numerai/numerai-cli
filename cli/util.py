import os
import sys
import subprocess
import shutil
import platform

import click
import boto3
import numerapi


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        client.list_buckets()
        return True

    except Exception as e:
        if 'NotSignedUp' in str(e):
            raise exception_with_msg(
                f"Your AWS keys are valid, but the account is not finished signing up. "
                f"You either need to update your credit card in AWS at "
                f"https://portal.aws.amazon.com/billing/signup?type=resubscribe#/resubscribed, "
                f"or wait up to 24 hours for their verification process to complete."
            )

        raise exception_with_msg(
            f"AWS keys seem to be invalid. Make sure you've entered them correctly "
            f"and that your user has the necessary permissions "
            f"(see https://github.com/numerai/numerai-cli/wiki/Prerequisites-Help)."
        )


def check_numerai_validity(key_id, secret):
    try:
        napi = numerapi.NumerAPI(key_id, secret)
        napi.get_account()
        return True

    except Exception:
        raise exception_with_msg(
            '''Numerai keys seem to be invalid. Make sure you've entered them correctly.'''
        )


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


def copy_files(src, dst, force=False, verbose=True):
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
            copy_files(src_file, dst_file, force=force, verbose=verbose)
        else:
            if verbose:
                click.secho(f"copying file {dst_file}", fg='yellow')
            shutil.copy(src_file, dst_file)


def get_package_dir():
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


def exception_with_msg(msg):
    return click.ClickException(msg)


def is_win10_professional():
    name = sys.platform
    if name != 'win32':
        return False

    version = platform.win32_ver()[0]

    if version == '10':
        # for windows 10 only, we need to know if it's pro vs home
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            return winreg.QueryValueEx(key, "EditionID")[0] == 'Professional'

    return False


# error checking for docker not being installed correctly
# sadly this is a mess, since there's tons of ways to mess up your docker install, especially on windows
def root_cause(err_msg):
    if b'is not recognized as an internal or external command' in err_msg:
        if sys.platform == 'win32':
            if is_win10_professional():
                raise exception_with_msg(
                    f"Docker does not appear to be installed. Make sure to download/install docker from "
                    f"https://hub.docker.com/editions/community/docker-ce-desktop-windows \n"
                    f"If you're sure docker is already installed,  then for some reason it isn't in your PATH like expected. "
                    f"Restarting may fix it.")

            else:
                raise exception_with_msg(
                    f"Docker does not appear to be installed. Make sure to download/install docker from "
                    f"https://github.com/docker/toolbox/releases and run 'Docker Quickstart Terminal' when you're done."
                    f"\nIf you're sure docker is already installed, then for some reason it isn't in your PATH like expected. "
                    f"Restarting may fix it.")

    if b'command not found' in err_msg:
        if sys.platform == 'darwin':
            raise exception_with_msg(
                f"Docker does not appear to be installed. You can install it with `brew cask install docker` or "
                f"from https://hub.docker.com/editions/community/docker-ce-desktop-mac")

        else:
            raise exception_with_msg(
                f"docker command not found. Please install docker "
                f"and make sure that the `docker` command is in your $PATH")

    if b'This error may also indicate that the docker daemon is not running' in err_msg or b'Is the docker daemon running' in err_msg:
        if sys.platform == 'darwin':
            raise exception_with_msg(
                f"Docker daemon not running. Make sure you've started "
                f"'Docker Desktop' and then run this command again.")

        elif sys.platform == 'linux2':
            raise exception_with_msg(
                f"Docker daemon not running or this user cannot acccess the docker socket. "
                f"Make sure docker is running and that your user has permissions to run docker. "
                f"On most systems, you can add your user to the docker group like so: "
                f"`sudo groupadd docker; sudo usermod -aG docker $USER` and then restarting your computer.")

        elif sys.platform == 'win32':
            if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ:
                raise exception_with_msg(
                    f"Docker daemon not running. Make sure you've started "
                    f"'Docker Quickstart Terminal' and then run this command again.")

            else:
                raise exception_with_msg(
                    f"Docker daemon not running. Make sure you've started "
                    f"'Docker Desktop' and then run this command again.")

    if b'invalid mode: /opt/plan' in err_msg:
        if sys.platform == 'win32':
            raise exception_with_msg(
                f"You're running Docker Toolbox, but you're not using the 'Docker Quickstart Terminal'. "
                f"Please re-run `numerai setup` from that terminal.")

    if b'Drive has not been shared' in err_msg:
        raise exception_with_msg(
            f"You're running from a directory that isn't shared to your docker Daemon. "
            f"Make sure your directory is shared through Docker Desktop: "
            f"https://docs.docker.com/docker-for-windows/#shared-drives")

    if b'No configuration files' in err_msg:
        raise exception_with_msg(
            "You're running from a directory that isn't shared to your docker Daemon. \
            Try running from a directory under your HOME, e.g. C:\\Users\\$YOUR_NAME\\$ANY_FOLDER"
        )

    if b'returned non-zero exit status 137' in err_msg:
        raise exception_with_msg(
            "Your docker container ran out of memory. Please open the docker desktop UI"
            " and increase the memory allowance in the advanced settings."
        )

    click.secho(f'Numerai CLI was unable to identify the following error:', fg='red')
    click.secho(err_msg.decode('utf8'), fg='red')