from pathlib import Path
import os
from os import path
import configparser
import shutil
import subprocess
import base64
import sys
import platform
from datetime import datetime

import click
import boto3
import numerapi
from colorama import init, Fore, Back, Style
import requests
import time


def exception_with_msg(msg):
    return click.ClickException(Fore.RED + msg)


def get_key_file():
    home = str(Path.home())

    return path.join(home, '.numerai')


class KeyConfig:
    def __init__(self, aws_public, aws_secret, numerai_public, numerai_secret):
        self._aws_public = aws_public
        self._aws_secret = aws_secret
        self._numerai_public = numerai_public
        self._numerai_secret = numerai_secret

    @property
    def aws_public(self):
        return self._aws_public

    @property
    def aws_secret(self):
        return self._aws_secret

    @property
    def numerai_public(self):
        return self._numerai_public

    @property
    def numerai_secret(self):
        return self._numerai_secret

    def sanitize_message(self, message):
        return message.replace(self.aws_public,
                               '...').replace(self.aws_secret, '...').replace(
                                   self.numerai_public,
                                   '...').replace(self.numerai_secret, '...')


def load_keys():
    key_file = get_key_file()

    config = configparser.ConfigParser()
    config.read(key_file)

    return KeyConfig(aws_public=config['default']['AWS_ACCESS_KEY_ID'],
                     aws_secret=config['default']['AWS_SECRET_ACCESS_KEY'],
                     numerai_public=config['default']['NUMERAI_PUBLIC_ID'],
                     numerai_secret=config['default']['NUMERAI_SECRET_KEY'])


def load_or_setup_keys():
    try:
        return load_keys()
    except:
        click.echo("Key file not found at: " + get_key_file())

    return setup_keys()


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3',
                              aws_access_key_id=key_id,
                              aws_secret_access_key=secret)
        client.list_buckets()
        return True

    except Exception as e:
        if 'NotSignedUp' in str(e):
            raise exception_with_msg(
                '''Your AWS keys are valid, but the account is not finished signing up. You either need to update your credit card in AWS at https://portal.aws.amazon.com/billing/signup?type=resubscribe#/resubscribed, or wait up to 24 hours for their verification process to complete.'''
            )

        raise exception_with_msg(
            '''AWS keys seem to be invalid. Make sure you've entered them correctly and that your user has the "AdministratorAccess" policy.'''
        )


def check_numerai_validity(key_id, secret):
    try:
        napi = numerapi.NumerAPI(key_id, secret)
        napi.get_user()
        return True

    except Exception:
        raise exception_with_msg(
            '''Numerai keys seem to be invalid. Make sure you've entered them correctly.'''
        )


def setup_keys():
    click.echo(Fore.YELLOW + "Setting up key file at " + get_key_file())

    click.echo()
    click.echo(Fore.RED + "Please type in the following keys:")
    aws_public = click.prompt('AWS_ACCESS_KEY_ID').strip()
    aws_private = click.prompt('AWS_SECRET_ACCESS_KEY').strip()
    numerai_public = click.prompt('NUMERAI_PUBLIC_ID').strip()
    numerai_private = click.prompt('NUMERAI_SECRET_KEY').strip()

    config = configparser.ConfigParser()
    config['default'] = {
        "AWS_ACCESS_KEY_ID": aws_public,
        "AWS_SECRET_ACCESS_KEY": aws_private,
        "NUMERAI_PUBLIC_ID": numerai_public,
        "NUMERAI_SECRET_KEY": numerai_private,
    }

    check_aws_validity(aws_public, aws_private)
    check_numerai_validity(numerai_public, numerai_private)

    with open(get_key_file(), 'w') as configfile:
        config.write(configfile)

    return load_keys()


def get_code_dir():
    return path.dirname(__file__)


def format_path_if_mingw(p):
    '''
    Helper function to format if the system is running docker toolbox + mingw. The paths need to be formatted like unix paths, and the drive letter needs to be lowercased
    '''
    if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ and 'MSYSTEM' in os.environ:
        p = '/' + p[0].lower() + p[2:]
        p = p.replace('\\', '/')
    return p


def get_project_numerai_dir():
    return path.join(os.getcwd(), ".numerai")


def get_docker_repo_file():
    return path.join(get_project_numerai_dir(), 'docker_repo.txt')


def get_submission_url_file():
    return path.join(get_project_numerai_dir(), 'submission_url.txt')


def read_docker_repo_file():
    docker_file = get_docker_repo_file()
    if not path.exists(docker_file):
        raise exception_with_msg(
            "docker repo not found. Make sure you have run `numerai setup` successfully before running this command."
        )

    with open(docker_file, 'r') as f:
        return f.read().strip()


def read_submission_url_file():
    f = get_submission_url_file()
    if not path.exists(f):
        raise exception_with_msg(
            "submission url file not found. Make sure you have run `numerai setup` successfully before running this command."
        )

    with open(f, 'r') as f:
        return f.read().strip()


def copy_terraform():
    click.echo("Creating .numerai directory in current project")
    shutil.copytree(path.join(get_code_dir(), "terraform"),
                    get_project_numerai_dir(),
                    copy_function=shutil.copy)


def copy_file(directory, filename, verbose, force):
    if verbose:
        click.echo(Fore.YELLOW + "copying " + filename)
    if os.path.exists(filename):
        overwrite = click.prompt(filename +
                                 ' already exists. Overwrite? [y]/n').strip()
        if overwrite != "" and overwrite != "y" and overwrite != "yes":
            return
    shutil.copy(path.join(directory, filename), filename)


def copy_docker_python3(verbose, force):
    code_dir = path.join(get_code_dir(), "examples", "python3")
    copy_file(code_dir, "Dockerfile", verbose, force)
    copy_file(code_dir, "model.py", verbose, force)
    copy_file(code_dir, "train.py", verbose, force)
    copy_file(code_dir, "predict.py", verbose, force)
    copy_file(code_dir, "requirements.txt", verbose, force)


def copy_docker_python3_multiaccount(verbose, force):
    code_dir = path.join(get_code_dir(), "examples", "python3-multiaccount")
    copy_file(code_dir, "Dockerfile", verbose, force)
    copy_file(code_dir, "model.py", verbose, force)
    copy_file(code_dir, "train.py", verbose, force)
    copy_file(code_dir, "predict.py", verbose, force)
    copy_file(code_dir, "requirements.txt", verbose, force)
    copy_file(code_dir, ".numerai-api-keys", verbose, force)
    if verbose:
        click.echo(
            Fore.RED +
            "You need to manually fill in all of your Numerai API keys in the .numerai-api-keys file that has been created for you in this directory."
        )


def copy_docker_rlang(verbose, force):
    code_dir = path.join(get_code_dir(), "examples", "rlang")
    copy_file(code_dir, "Dockerfile", verbose, force)
    copy_file(code_dir, "install_packages.R", verbose, force)
    copy_file(code_dir, "main.R", verbose, force)


def is_win10_professional():
    name = sys.platform
    if name != 'win32':
        return False

    version = platform.win32_ver()[0]

    if version == '10':
        # for windows 10 only, we need to know if it's pro vs home
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            return winreg.QueryValueEx(key, "EditionID")[0] == 'Professional'

    return False


def terraform_setup(verbose, cpu, memory):
    if path.abspath(os.getcwd()) == path.abspath(str(Path.home())):
        raise exception_with_msg(
            "`numerai setup` cannot be run from your $HOME directory. Please create another directory and run this again."
        )

    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        copy_terraform()

    if cpu is not None or memory is not None:
        if cpu is None:
            cpu = 1024
        if memory is None:
            memory = 8192

        with open(path.join(get_code_dir(), "terraform_variables_template.tf"),
                  'r') as template:
            with open(path.join(get_project_numerai_dir(), 'variables.tf'),
                      'w') as out:
                out.write(template.read().format(fargate_cpu=cpu,
                                                 fargate_memory=memory))

    # Format path for mingw after checking that it exists
    numerai_dir = format_path_if_mingw(numerai_dir)

    keys = load_or_setup_keys()

    c = "docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light init".format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True, stderr=subprocess.PIPE)

    # error checking for docker not being installed correctly
    # sadly this is a mess, since there's tons of ways to mess up your docker install, especially on windows
    if res.returncode != 0:
        if b'is not recognized as an internal or external command' in res.stderr:
            if sys.platform == 'win32':
                if is_win10_professional():
                    raise exception_with_msg(
                        '''Docker does not appear to be installed. Make sure to download/install docker from https://hub.docker.com/editions/community/docker-ce-desktop-windows

If you're sure docker is already installed, then for some reason it isn't in your PATH like expected. Restarting may fix it.'''
                    )
                else:
                    raise exception_with_msg(
                        '''Docker does not appear to be installed. Make sure to download/install docker from https://github.com/docker/toolbox/releases and run "Docker Quickstart Terminal" when you're done.

If you're sure docker is already installed, then for some reason it isn't in your PATH like expected. Restarting may fix it.'''
                    )
        if b'command not found' in res.stderr:
            if sys.platform == 'darwin':
                raise exception_with_msg(
                    '''Docker does not appear to be installed. You can install it with `brew cask install docker` or from https://hub.docker.com/editions/community/docker-ce-desktop-mac'''
                )
            else:
                raise exception_with_msg(
                    '''docker command not found. Please install docker and make sure that the `docker` command is in your $PATH'''
                )

        if b'This error may also indicate that the docker daemon is not running' in res.stderr or b'Is the docker daemon running' in res.stderr:
            if sys.platform == 'darwin':
                raise exception_with_msg(
                    '''Docker daemon not running. Make sure you've started "Docker Desktop" and then run this command again.'''
                )
            elif sys.platform == 'linux2':
                raise exception_with_msg(
                    '''Docker daemon not running or this user cannot acccess the docker socket. Make sure docker is running and that your user has permissions to run docker. On most systems, you can add your user to the docker group like so: `sudo groupadd docker; sudo usermod -aG docker $USER` and then restarting your computer.'''
                )
            elif sys.platform == 'win32':
                if 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ:
                    raise exception_with_msg(
                        '''Docker daemon not running. Make sure you've started "Docker Quickstart Terminal" and then run this command again.'''
                    )
                else:
                    raise exception_with_msg(
                        '''Docker daemon not running. Make sure you've started "Docker Desktop" and then run this command again.'''
                    )
                # else:
        if b'invalid mode: /opt/plan' in res.stderr:
            if sys.platform == 'win32':
                raise exception_with_msg(
                    '''It appears that you're running Docker Toolbox, but you're not using the "Docker Quickstart Terminal". Please re-run `numerai setup` from that terminal.'''
                )
        if b'Drive has not been shared' in res.stderr:
            raise exception_with_msg(
                r'''It appears that you're running from a directory that isn't shared to your docker Daemon. Make sure your directory is shared through Docker Desktop: https://docs.docker.com/docker-for-windows/#shared-drives'''
            )

        print(res.stderr.decode('utf8'), file=sys.stderr)

    res.check_returncode()
    click.echo('succesfully setup .numerai with terraform')

    c = '''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))

    if sys.platform == 'win32' and 'DOCKER_TOOLBOX_INSTALL_PATH' in os.environ:
        click.echo(
            'running aws setup through terraform. this can take a few minutes')
        res = subprocess.run(c,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        if res.returncode != 0:
            if b'No configuration files' in res.stdout:
                raise exception_with_msg(
                    r'''It appears that you're running from a directory that isn't shared to your docker Daemon. Try running from a directory under your HOME, e.g. C:\Users\$YOUR_NAME\$ANY_FOLDER'''
                )

        print(res.stdout.decode('utf8'))
        print(res.stderr.decode('utf8'), file=sys.stderr)
    else:
        res = subprocess.run(c, shell=True)

    res.check_returncode()

    c = '''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output docker_repo'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True, stdout=subprocess.PIPE)

    with open(get_docker_repo_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())
    click.echo(Fore.YELLOW + 'wrote docker repo to: ' + get_docker_repo_file())

    c = '''docker run --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light output submission_url'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True, stdout=subprocess.PIPE)

    with open(get_submission_url_file(), 'w') as f:
        f.write(res.stdout.decode('utf-8').strip())
    click.echo(Fore.YELLOW + 'wrote submission url to: ' +
               get_submission_url_file())


def terraform_destroy(verbose):
    numerai_dir = get_project_numerai_dir()
    if not path.exists(numerai_dir):
        return
    numerai_dir = format_path_if_mingw(numerai_dir)

    keys = load_or_setup_keys()

    c = '''docker run -e "AWS_ACCESS_KEY_ID={keys.aws_public}" -e "AWS_SECRET_ACCESS_KEY={keys.aws_secret}" --rm -it -v {numerai_dir}:/opt/plan -w /opt/plan hashicorp/terraform:light destroy -auto-approve'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + keys.sanitize_message(c))
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@click.group()
def cli():
    """This script allows you to setup Numer.ai compute node and deploy docker containers to it"""
    pass


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option(
    '--cpu',
    '-c',
    help=
    "the cpu to use in the compute container (defaults to 1024). See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings",
    type=(int))
@click.option(
    '--memory',
    '-m',
    help=
    "the memory to use in the compute container (defaults to 8192). See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for possible settings",
    type=(int))
def setup(verbose, cpu, memory):
    """Sets up a Numer.ai compute node in AWS"""
    terraform_setup(verbose, cpu, memory)


@click.command()
@click.option('--verbose', '-v', is_flag=True)
def destroy(verbose):
    """Destroys a previously setup Numer.ai compute node"""
    terraform_destroy(verbose)


@click.group()
def docker():
    """A collection of docker commands for building/deploying a docker image"""
    pass


@docker.command()
@click.option('--quiet', '-q', is_flag=True)
@click.option('--force', '-f', is_flag=True)
@click.option('--rlang', '-r', is_flag=True)
@click.option('--python3-multiaccount', '-m', is_flag=True)
def copy_example(quiet, force, rlang, python3_multiaccount):
    """Copies a few example files into the current directory"""
    if rlang:
        copy_docker_rlang(not quiet, force)
    elif python3_multiaccount:
        copy_docker_python3_multiaccount(not quiet, force)
    else:
        copy_docker_python3(not quiet, force)

    with open('.dockerignore', 'a+') as f:
        f.write(".numerai\n")
        f.write("numerai_dataset.zip\n")
        f.write(".git\n")


def docker_build(verbose):
    docker_repo = read_docker_repo_file()

    keys = load_keys()

    c = '''docker build -t {docker_repo} --build-arg NUMERAI_PUBLIC_ID={keys.numerai_public} --build-arg NUMERAI_SECRET_KEY={keys.numerai_secret} .'''.format(
        **locals())
    if verbose:
        click.echo("running: " + keys.sanitize_message(c))

    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--command', '-c', default='python train.py', type=(str))
@click.option('--verbose', '-v', is_flag=True)
def train(command, verbose):
    """
    Run the docker image locally and output trained models. This runs train.py (by default)
    """
    docker_build(verbose)

    docker_repo = read_docker_repo_file()
    cur_dir = format_path_if_mingw(os.getcwd())

    c = '''docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {docker_repo} {command}'''.format(
        **locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def run(verbose):
    """
    Run the docker image locally and submit predictions. This runs the default CMD in your docker container (predict.py if you're using the example)
    """
    docker_build(verbose)

    docker_repo = read_docker_repo_file()
    cur_dir = format_path_if_mingw(os.getcwd())

    c = '''docker run --rm -it -v {cur_dir}:/opt/app -w /opt/app {docker_repo} '''.format(
        **locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def build(verbose):
    """Builds the docker image"""
    docker_build(verbose)


def docker_cleanup(verbose):
    keys = load_keys()

    ecr_client = boto3.client('ecr',
                              region_name='us-east-1',
                              aws_access_key_id=keys.aws_public,
                              aws_secret_access_key=keys.aws_secret)

    resp = ecr_client.list_images(repositoryName='numerai-submission',
                                  filter={
                                      'tagStatus': 'UNTAGGED',
                                  })

    imageIds = resp['imageIds']
    if len(imageIds) == 0:
        return

    resp = ecr_client.batch_delete_image(
        repositoryName='numerai-submission',
        imageIds=imageIds,
    )

    imageIds = resp['imageIds']
    if len(imageIds) > 0:
        click.echo(Fore.YELLOW + "deleted " + str(len(imageIds)) +
                   " old image(s) from remote docker repo")


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def cleanup(verbose):
    docker_cleanup(verbose)


@docker.command()
@click.option('--verbose', '-v', is_flag=True)
def deploy(verbose):
    """Deploy the docker image to the Numer.ai compute node"""
    docker_build(verbose)

    docker_repo = read_docker_repo_file()

    keys = load_keys()

    ecr_client = boto3.client('ecr',
                              region_name='us-east-1',
                              aws_access_key_id=keys.aws_public,
                              aws_secret_access_key=keys.aws_secret)

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(
        token['authorizationData'][0]['authorizationToken']).decode().split(
            ':')

    if verbose:
        click.echo('running: docker login')
    res = subprocess.run(
        '''docker login -u {username} -p {password} {docker_repo}'''.format(
            **locals()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    res.check_returncode()

    c = '''docker push {docker_repo}'''.format(**locals())
    if verbose:
        click.echo('running: ' + c)
    res = subprocess.run(c, shell=True)
    res.check_returncode()

    docker_cleanup(verbose)


@click.group()
def compute():
    """A collection of compute commands for inspecting your running compute node"""
    pass


@compute.command()
@click.option('--quiet', '-q', is_flag=True)
def test_webhook(quiet):
    """
    This will POST to your webhook, and trigger compute to run in the cloud

    You can observe the logs for the running job by running `numerai compute logs`
    """
    url = read_submission_url_file()

    round_json = {
        "roundNumber": -1,
        "dataVersion": 1,
    }

    req = requests.post(url, json=round_json)

    req.raise_for_status()

    if not quiet:
        click.echo("request success")
        click.echo(req.json())

        click.echo(
            Fore.YELLOW +
            "You can now run `numerai compute status` or `numerai compute logs` to see your compute node running. Note that `numerai compute logs` won't work until the task is in the RUNNING state, so watch `numerai compute status` for that to happen."
        )


def get_latest_task(keys, verbose):
    ecs_client = boto3.client('ecs',
                              region_name='us-east-1',
                              aws_access_key_id=keys.aws_public,
                              aws_secret_access_key=keys.aws_secret)
    tasks = ecs_client.list_tasks(cluster='numerai-submission-ecs-cluster',
                                  desiredStatus="RUNNING")
    if len(tasks["taskArns"]) == 0:
        tasks = ecs_client.list_tasks(cluster='numerai-submission-ecs-cluster',
                                      desiredStatus="STOPPED")

    if len(tasks["taskArns"]) == 0:
        return None

    tasks = ecs_client.describe_tasks(cluster='numerai-submission-ecs-cluster',
                                      tasks=[tasks["taskArns"][0]])

    return tasks['tasks'][0]


@compute.command()
@click.option('--verbose', '-v', is_flag=True)
def status(verbose):
    """
    Get the status of the latest task in compute
    """
    keys = load_keys()

    task = get_latest_task(keys, verbose)

    if task is None:
        raise exception_with_msg(
            "No tasks in the PENDING/RUNNING/STOPPED state found. This may mean that your task has been finished for a long time, and no longer exists. Check `numerai compute logs` and `numerai compute logs -l lambda` to see what happened."
        )

    click.echo("task ID: " + task["taskArn"])
    click.echo("status : " + task["lastStatus"])
    click.echo("created: " + str(task["createdAt"]))


@compute.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option('--num-lines',
              '-n',
              help="the number of log lines to return",
              default=20,
              type=(int))
@click.option(
    "--log-type",
    "-l",
    help=
    "the log type to lookup. Options are fargate|lambda. Default is fargate",
    default="fargate")
@click.option("--follow-tail",
              "-f",
              help="tail the logs constantly",
              is_flag=True)
def logs(verbose, num_lines, log_type, follow_tail):
    """
    Get the logs from the last run task

    Keep in mind, logs are not created until a task is in the RUNNING state, so the logs returned by this command might be out of date
    """
    def print_logs(events, limit):
        if len(events["events"]) == limit:
            click.echo(
                '...more log lines available: use -n option to get more...')
        for event in events["events"]:
            click.echo(
                str(datetime.fromtimestamp(event['timestamp'] / 1000)) + ':' +
                event['message'])

    def get_name_and_print_logs(logs_client,
                                family,
                                limit,
                                nextToken=None,
                                raise_on_error=True):
        streams = logs_client.describe_log_streams(logGroupName=family,
                                                   orderBy="LastEventTime",
                                                   descending=True)

        if len(streams['logStreams']) == 0:
            if not raise_on_error:
                return False
            raise exception_with_msg(
                "No logs found. Make sure the webhook has triggered (check 'numerai compute logs -l lambda'). If it has, then check `numerai compute status` and make sure it's in the RUNNING state (this can take a few minutes). Also, make sure your webhook has triggered at least once by running 'curl `cat .numerai/submission_url.txt`'"
            )
        name = streams['logStreams'][0]['logStreamName']

        kwargs = {}  # boto is weird, and doesn't allow `None` for parameters
        if nextToken is not None:
            kwargs['nextToken'] = nextToken
        if limit is not None:
            kwargs['limit'] = limit
        events = logs_client.get_log_events(logGroupName=family,
                                            logStreamName=name,
                                            **kwargs)
        click.echo("log for " + family + ":" + name + ":")
        print_logs(events, limit)
        return True

    keys = load_keys()

    logs_client = boto3.client('logs',
                               region_name='us-east-1',
                               aws_access_key_id=keys.aws_public,
                               aws_secret_access_key=keys.aws_secret)

    if log_type == "fargate":
        family = "/fargate/service/numerai-submission"
    elif log_type == "lambda":
        family = "/aws/lambda/numerai-submission"
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        return
    else:
        raise exception_with_msg(
            "Unknown log type, expected 'fargate' or 'lambda': got " +
            log_type)

    def latest_task_printer(task, keys, verbose):
        if task is None:
            click.echo(Fore.RED + "task not found or is in the STOPPED state")
        elif task['desiredStatus'] == 'RUNNING' and task[
                'lastStatus'] != 'RUNNING':
            click.echo(
                Fore.RED +
                "there is another task in the PENDING state. Check its status with `numerai compute status` and then rerun the logs command once it is RUNNING."
            )

    def task_status(task):
        ecs_client = boto3.client('ecs',
                                  region_name='us-east-1',
                                  aws_access_key_id=keys.aws_public,
                                  aws_secret_access_key=keys.aws_secret)
        resp = ecs_client.describe_tasks(
            cluster='numerai-submission-ecs-cluster', tasks=[task["taskArn"]])

        tasks = resp['tasks']
        if len(tasks) == 0:
            return None
        return tasks[0]

    def get_log_for_task_id(task_id):
        streams = logs_client.describe_log_streams(logGroupName=family,
                                                   orderBy="LastEventTime",
                                                   descending=True)
        if len(streams['logStreams']) == 0:
            raise exception_with_msg(
                "No logs found. Make sure the webhook has triggered (check 'numerai compute logs -l lambda'). If it has, then check `numerai compute status` and make sure it's in the RUNNING state (this can take a few minutes). Also, make sure your webhook has triggered at least once by running 'curl `cat .numerai/submission_url.txt`'"
            )

        for stream in streams['logStreams']:
            if stream['logStreamName'].endswith(task_id):
                return stream['logStreamName']
        return None

    task = get_latest_task(keys, verbose)
    if task is None:
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        return

    status = task_status(task)
    if status is None or status["lastStatus"] == "STOPPED":
        get_name_and_print_logs(logs_client, family, limit=num_lines)
        latest_task_printer(task, keys, verbose)
        return

    task_id = task["taskArn"].split('/')[-1]

    name = get_log_for_task_id(task_id)
    if name is None:
        print("Log file has not been created yet. Waiting.", end='')
    while name is None:
        print('.', end='')
        time.sleep(2)
        name = get_log_for_task_id(task_id)

    task = get_latest_task(keys, verbose)
    events = logs_client.get_log_events(logGroupName=family,
                                        logStreamName=name,
                                        limit=num_lines)

    click.echo("log for " + family + ":" + name + ":")
    print_logs(events, num_lines)

    if follow_tail:
        while True:
            events = logs_client.get_log_events(
                logGroupName=family,
                logStreamName=name,
                nextToken=events['nextForwardToken'])
            for event in events["events"]:
                click.echo(
                    str(datetime.fromtimestamp(event['timestamp'] / 1000)) +
                    ':' + event['message'])
            status = task_status(task)["lastStatus"]
            if status != "RUNNING":
                click.echo(Fore.YELLOW + "Task is now in the " + status +
                           " state")
                return


def main():
    init(autoreset=True)

    cli.add_command(setup)
    cli.add_command(destroy)

    cli.add_command(docker)
    cli.add_command(compute)
    cli()


if __name__ == "__main__":
    main()
