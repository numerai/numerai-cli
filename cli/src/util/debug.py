import os
import sys
import platform

import click


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
# sadly this is a mess, since there's tons of ways to mess up your docker install,
# especially on windows :(
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

    raise exception_with_msg(
        f'Numerai CLI was unable to identify the error, please try to use the '
        f'"--verbose|-v" option for more information before reporting this\n'
        + err_msg.decode('utf8')
    )
