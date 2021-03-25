import json
import subprocess
import sys
from urllib import request

import click

from numerai.cli.util.files import load_or_init_nodes
from numerai.cli.util.debug import is_win8, is_win10
from numerai.cli.util.keys import \
    check_aws_validity, \
    check_numerai_validity, \
    get_numerai_keys, \
    get_aws_keys


@click.command()
def doctor():
    """
    Checks and repairs your environment in case of errors.
    Attempts to provide information to debug your local machine.
    """
    # Check environment pre-reqs
    click.secho("Running the environment setup script for your OS...")
    env_setup_cmd = None
    env_setup_status = -1
    env_setup_err = ''
    if sys.platform == "linux" or sys.platform == "linux2":
        env_setup_cmd = 'sudo apt update && sudo apt install -y libcurl4 curl && ' \
                        'sudo curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-ubu.sh ' \
                        '| sudo bash'

    elif sys.platform == "darwin":
        env_setup_cmd = 'curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-mac.sh | bash'

    elif is_win10():
        env_setup_cmd = 'powershell -command "$Script = Invoke-WebRequest ' \
                        '\'https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-win10.ps1\'; ' \
                        '$ScriptBlock = [ScriptBlock]::Create($Script.Content); Invoke-Command -ScriptBlock $ScriptBlock"'

    elif is_win8():
        # TODO: check if more is needed?
        env_setup_cmd = 'docker info'

    else:
        env_setup_status = 1
        env_setup_err = f"Unrecognized Operating System {sys.platform}, " \
                        f"cannot run environment setup script, skipping..."

    if env_setup_cmd is not None:
        res = subprocess.run(
            env_setup_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        env_setup_status = res.returncode
        env_setup_err = res.stderr

    # Check official (non-dev) version
    click.secho(f"Checking your numerai-cli version...")
    res = str(subprocess.run(
        'pip3 show numerai-cli',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    ))
    curr_ver = [s for s in res.split('\\n') if 'Version:' in s][0].split(': ')[1]
    url = f"https://pypi.org/pypi/numerai-cli/json"
    versions = list(reversed(sorted(filter(
        lambda key: 'dev' not in key,
        json.load(request.urlopen(url))["releases"].keys()
    ))))

    # Check keys
    click.secho("Checking your API keys...")
    nodes_config = load_or_init_nodes()
    used_providers = [nodes_config[n]['provider'] for n in nodes_config]

    invalid_providers = []
    try:
        check_numerai_validity(*get_numerai_keys())
    except:
        invalid_providers.append('numerai')
    if 'aws' in used_providers:
        try:
            check_aws_validity(*get_aws_keys())
        except:
            invalid_providers.append('aws')

    if env_setup_status != 0:
        click.secho(f"✖ Environment setup incomplete:", fg='red')
        click.secho(env_setup_err, fg='red')
        click.secho(f"Ensure your OS is supported and read the Troubleshooting wiki: "
                    f"https://github.com/numerai/numerai-cli/wiki/Troubleshooting", fg='red')
    else:
        click.secho("✓ Environment setup with Docker and Python", fg='green')

    if curr_ver < versions[0]:
        click.secho(f"✖ numerai-cli needs an upgrade"
                    f"(run `pip3 install -U numerai-cli` to fix)", fg='red')
    else:
        click.secho("✓ numerai-cli is up to date", fg='green')

    if len(invalid_providers):
        click.secho(f"✖ Invalid provider keys: {invalid_providers}"
                    f"(run `numerai setup` to fix)", fg='red')

    else:
        click.secho("✓ API Keys working", fg='green')

    click.secho(
        "\nIf you need help troubleshooting or want to report a bug please read the" 
        "\nTroubleshooting and Feedback section of the readme:"
        "\nhttps://github.com/numerai/numerai-cli#troubleshooting-and-feedback",
        fg='yellow'
    )
