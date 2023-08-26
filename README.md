# numerai-cli

[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

Welcome to the Numerai CLI for the [Numerai Tournament](https://docs.numer.ai/tournament/learn).
This README is designed to have EVERYTHING you need to setup and maintain a Numerai Compute Heavy node.

This CLI runs on your local computer to configure a Numerai Prediction Node in the cloud.
This solution is architected to cost less than $5/mo on average, but actual costs may vary.
It has been tested on MacOS/OSX, Windows 8/10, and Ubuntu 18/20,
but should theoretically work anywhere that Docker and Python 3 are available.

## Contents

- [Getting Started](#getting-started)
  - [List of Commands](#list-of-commands)
  - [Upgrading](#upgrading)
    - [Upgrading from 0.1/0.2 to 0.3.0](#upgrading-from-0102-to-030)
    - [Beyond](#beyond)
  - [Uninstalling](#uninstalling)
- [Troubleshooting and Feedback](#troubleshooting-and-feedback)
  - [Python](#python)
  - [Docker](#docker)
    - [MacOS and Windows 10](#macos-and-windows-10)
    - [Linux](#linux)
    - [Older PCs: Docker Toolbox](#older-pcs-docker-toolbox)
  - [Azure](#azure)
  - [Common Errors](#common-errors)
- [Billing Alerts](#billing-alerts)
- [Prediction Node Architecture](#prediction-node-architecture)
  - [Python Example](#python-example)
  - [RLang Example](#rlang-example)
  - [The Dockerfile](#the-dockerfile)
  - [Cloud Components](#cloud-components)
- [Special Thanks](#special-thanks)

## Getting Started

To use this tool you need:

- Numerai API keys
- Paid cloud provider account
- Python
- Docker

1. Sign up a Numerai Account, get your Numerai API Keys, and your first Model:

   1. Sign up at <https://numer.ai/signup> and log in to your new account
   2. Go to <https://numer.ai/account> > "Your API keys" section > click "Add"
   3. Name your key and check all boxes under "Scope this key will have"
   4. Enter your password and click "Confirm"
   5. Copy your secret public key and secret key somewhere safe

2. Choose your cloud provider and follow the corresponding guide:

   - [AWS Setup Guide](./docs/aws_setup_guide.md)
   - [Azure Setup Guide](./docs/azure_setup_guide.md)

3. Install Docker and Python for your Operating System (if you encounter errors or your
   OS is not supported, please see [Troubleshooting and Feedback](#troubleshooting-and-feedback)):

   - Mac Terminal (cmd + space, type `terminal`, select `terminal.app`):

     ```shell
     curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-mac.sh | bash
     ```

   - Ubuntu 18/20 Terminal (ctrl + alt + t):

     ```shell
     sudo apt update && sudo apt install -y libcurl4 curl && sudo curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-ubu.sh | sudo bash
     ```

   - Windows 10 Command Prompt (windows key, type `cmd`, select Command Prompt):

     ```powershell
     powershell -command "$Script = Invoke-WebRequest 'https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-win10.ps1'; $ScriptBlock = [ScriptBlock]::Create($Script.Content); Invoke-Command -ScriptBlock $ScriptBlock"
     ```

4. After the setup script confirms Python and Docker, install `numerai-cli` via:

   ```shell
   pip3 install --upgrade numerai-cli --user
   ```

   NOTES:

   - This command will also work to update to new versions of the package in the future.
   - If you are using python venv then drop the --user option.
     If you don't know what that is, disregard this note.

5. Run these commands on your personal computer (not a temporary instance)
   to get an example node running in minutes:

   For AWS run:

   ```shell
   numerai setup --provider aws
   ```

   For Azure users run:

   ```shell
   numerai setup --provider azure
   ```

   ```shell
   numerai node config --example tournament-python3
   numerai node deploy
   numerai node test
   ```

   If you want to use larger instances to generate your predictions first run `numerai list-constants`
   to list the vCPU/mem presets available, then you can configure a node to use one of the presets via:

   ```shell
   numerai node config -s mem-lg
   ```

   Your compute node is now setup and ready to run! When you make changes to your code or re-train your model,
   simply deploy and test your node again:

   ```shell
   numerai node deploy
   numerai node test
   ```

   NOTES:

   - These commands have stored configuration files in `$USER_HOME/.numerai/`. DO NOT LOSE THIS FILE!
     or else you will have to manually delete every cloud resource by hand.
   - The example node trains a model in the cloud, which is bad. You should train locally, pickle the
     trained model, deploy your node, then unpickle your model to do the live predictions
   - The default example does _not_ make stake changes; please refer to the [numerapi docs](https://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
     for the methods you must call to do this.
   - You can view resources and logs in the AWS Console (region us-east-1) for your
     [ECS Cluster](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks)
     and [other resources](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)

### List of Commands

Use the `--help` option on any command or sub-command to get a full description of it:

```shell
numerai
numerai --help
numerai [command] --help
numerai [command] [sub-command] --help
```

Each command or sub-command takes its own options, for example if you want to copy the
numerai signals example and configure a node for a signals model with large memory
requirements you'd use something like this (replacing [MODEL NAME] with the relevant
signals model name):

```shell
numerai node -m [MODEL NAME] -s config -s mem-lg -e signals-python3
```

Here, the `node` command takes a model name with `-m` and a flag `-s` to detect if it's
a signals model or numerai model. The `config` sub-command also takes a `-s` option to
specify the size of the node to configure.

### Upgrading

Upgrading numerai-cli will always require you to update the package itself using pip:

```shell
pip install --upgrade numerai-cli --user
numerai upgrade
```

#### 0.1/0.2 to 0.3

CLI 0.3 uses a new configuration format that is incompatible with versions 0.1 and 0.2,
but a command to migrate you configuration is provided for you. Run this in the directory
you ran `numerai setup` from the previous version:

```shell
numerai upgrade
```

#### 0.3 to 0.4

CLI 0.4 introduces a new provider option (Microsoft Azure) and moves the default aws
terraform into a subdirectory. You'll need to run `upgrade`:

```shell
numerai upgrade
```

If you want to use azure, follow the [setup guide for azure](./docs/azure_setup_guide.md)
then run:

```shell
numerai setup --provider azure
numerai node config --provider azure
```

#### Beyond

Some updates will make changes to configuration files used by Numerai CLI. These will
require you to re-run some commands to upgrade your nodes to the newest versions:

- `numerai setup` will copy over changes to files in the `$HOME/.numerai` directory
- `numerai node config` will apply those changes to a node

### Uninstalling

```shell
numerai uninstall
```

## Troubleshooting and Feedback

Please review this entire section and check github issues before asking questions.
If you've exhausted this document, then join us on Discord

If you still cannot find a solution or answer, please join us on
[Discord](https://discord.gg/numerai)
and include the following information with your issue/message:

- The commands you ran that caused the error (even previous commands)
- Version information from running:
  - `pip3 show numerai-cli`
  - `python -V`
  - `docker -v`
- System Information from running
  - Mac: `system_profiler SPSoftwareDataType && system_profiler SPHardwareDataType`
  - Linux: `lsb_release -a && uname -a`
  - Windows: `powershell -command "Get-ComputerInfo"`

### Python

If the environment setup script fails to install Python3 for you, report the error to Numerai
and then install it manually with one of the following options:

- [Download Python3 directly](https://www.python.org/downloads/)
- install it from [your system's package manager](https://en.wikipedia.org/wiki/List_of_software_package_management_systems)
- Use [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) to install and manage python for you

### Docker

If the environment setup script fails to install Docker for you, report the error to Numerai
then read the following to get a working installation on your machine. For PCs, you may need to [activate virtualization in your BIOS](https://superuser.com/questions/1382472/how-do-i-find-and-enable-the-virtualization-setting-on-windows-10) before installing.

#### MacOS and Windows 10

Just install [Docker Desktop](https://www.docker.com/products/docker-desktop) to get it running.
You should also increase the RAM allocated to the VM:

1. Open the Docker Desktop GUI then
2. Click Gear in top right corner
3. Select Resources > Advanced in left sidebar
4. Use slider to allocate more memory (leave a few gigs for your OS and background applications, otherwise your computer might crash)

#### Linux

Check here for instructions for your distribution:
<https://docs.docker.com/engine/install/>

#### Older PCs: Docker Toolbox

If your machine is older and/or doesn't have Hyper-V enabled, then you will have to follow these steps to install docker toolbox on your machine:

1. [Install Oracle VirtualBox](https://www.virtualbox.org/wiki/Downloads) for your Operating System
2. Restart your computer
3. [Install Docker Toolbox](https://github.com/docker/toolbox/releases)
4. Restart your computer
5. After it's installed, open the "Docker QuickStart Terminal" and run the following to increase its RAM:

```shell
docker-machine rm default
docker-machine create -d virtualbox --virtualbox-cpu-count=2 --virtualbox-memory=4096 --virtualbox-disk-size=50000 default
docker-machine restart default
```

NOTE: your code must live somewhere under your User directory (ie. C:\Users\USER_NAME\ANY_FOLDER). This is a restriction of docker toolbox not sharing paths correctly otherwise.

### Azure

If you just made your Azure account there's a chance your account provisioning could take some time, potentially up to 24 hours.

When configuring your node for the first time the numerai-cli may hang as it tries to provision infrastructure in your account. If running `numerai node config --provider azure` shows no log output for more than 5 minutes, your account is likely in the stuck provisioning state. While we investigate this issue, the best course of action is to wait until the following day and run the command again as there is no way to skip this Azure provisioning step.

### Common Errors

```shell
Error:
subprocess.CalledProcessError: Command 'docker run --rm -it -v /home/jason/tmp/.numerai:/opt/plan -w /opt/plan hashicorp/terraform:light init' returned non-zero exit status 127.


Reason:
Docker is not installed.

Solutions:
If you're certain that docker is installed, make sure that your user can execute docker, ie. try to run `docker ps`.
If that's the issue, then depending on your system, you can do the following:

- Windows/OSX
    - Make sure the Docker Desktop is running and finished booting up.
      It can take a few minutes to be completely ready.
      When clicking on the docker tray icon, it should say "Docker Desktop is Running".
    - If you're using Docker Toolbox on Windows, then make sure you've opened the "Docker Quickstart Terminal".

- Linux
    - Run `sudo usermod -aG docker $USER`
    - Then reboot or logout/login for this to take effect.
```

```shell
Error:
docker: Error response from daemon: Drive has not been shared

Solutions:
- You need to [share your drive](https://docs.docker.com/docker-for-windows/#shared-drives).
```

```shell
Error:
numerai: command not found

Solutions:
- osx/linux: Try and run `~/.local/bin/numerai`
- Windows: `%LOCALAPPDATA%\Programs\Python\Python37-32\Scripts\numerai.exe`
- Alternatively, exit then re-open your terminal/command prompt.
```

```shell
Error:
error calling sts:GetCallerIdentity: InvalidClientTokenId: The security token included in the request is invalid.
...
Command 'docker run -e "AWS_ACCESS_KEY_ID=..." -e "AWS_SECRET_ACCESS_KEY=..." --rm -it -v /home/jason/tmp/.numerai:/opt/plan -w /opt/planhashicorp/terraform:light apply -auto-approve' returned non-zero exit status 1.

Solutions:
- Run `numerai configure` to re-write your API Keys
```

```shell
Error:
ERROR numerapi.base_api: Error received from your webhook server: {"tasks":[],"failures":[{"reason":"The requested CPU configuration is above your limit"}]}

Solution:
1. Go to the [Quota Dashboard for EC2](console.aws.amazon.com/servicequotas/home/services/ec2/quotas)
2. Search for "On-Demand", this will list all instance types and their limits for your account.
3. Click the bubble next to "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances"
4. click "Request quota increase" in the top right
5. Input a higher value than the currently applied quota and finish the request
```

- If after AWS increases your quota, you still get this error, try again 1-2 more times
- You may have to complete a quota request for other types of instances too depending on how resource intensive your setup is

## Billing Alerts

There's no automated way to setup billing alerts, so you'll need to
[configure one manually](https://www.cloudberrylab.com/resources/blog/how-to-configure-billing-alerts-for-your-aws-account/).
We estimate costs to be less than $5 per month unless your compute takes more than 12 hours a week,
but increasing the RAM/CPU will increase your costs.

## Prediction Node Architecture

A Prediction Node represents a cloud-based model that Numerai can trigger for predictions; it is designed to be reliable, resource efficient, and easy to configure and debug. Prediction Nodes use a few important components like a `Dockerfile`, a `Trigger`, a `Container`, and a `Compute Cluster`, all of which can be created using one of the following examples.

### Python Example

```shell
numerai-python3
├── Dockerfile
├── .dockerignore
├── predict.py
├── requirements.txt
└── train.py
```

- `Dockerfile`: Used during `numerai node deploy` to build a Docker image that's used to run your code in the cloud. It copies all files in its directory, installs Python requirements for requirements.txt, and runs `python predict.py` by default.

- `.dockerignore`: This file uses regex to match files that should not be included in the Docker image.

- `train.py`: This is an extra entry point specifically for training, it's used when running `numerai node test --local --command "python train.py"`

- `requirements.txt`: Defines python packages required to run the code.
- `predict.py`: Gets run by default locally and in the cloud when running `numerai test` without the `--command|-c` option.

### RLang Example

```shell
numerai-rlang
├── Dockerfile
├── .dockerignore
├── install_packages.R
└── main.R
```

- `Dockerfile`: Used during `numerai node deploy` to build a Docker image that's used to run your code in the cloud. It copies all files in its directory, installs Rlang requirements from install_packages.R, and runs main.R by default.

- `.dockerignore`: This file uses regex to match files that should not be included in the Docker image.

- `install_packages.R`: Installs dependencies necessary for running the example.
- `main.R`: Ran by default locally and in the cloud and when running `numerai test` without the `--command|-c` option.

### The Dockerfile

This is the most important component of deploying a Prediction Node. It is a program (much like a bash script), that packages up your code as an `image`; this image contains everything your code needs to run in the cloud. The most typical case of a Dockerfile is demonstrated in [Numerai Examples](./numerai/examples/), if you're not sure how to use a Dockerfile, first copy an example with `numerai copy-example`, then read the documentation in the Dockerfile to learn the basics.

These files are very flexible, the default Dockerfile will just copy everything in whatever directory it is in, but this can be customized if you'd like to share code between models. For example, if you have a python project setup like so:

```shell
numerai_models
├── common
├──── __init__.py
├──── data.py
├──── setup.py
├── model_1
├──── Dockerfile
├──── .dockerignore
├──── predict.py
├──── requirements.txt
└──── train.py
```

Where `common` is an installable python package you want to use in multiple models, you can add this line to model_1/Dockerfile: `RUN pip install ../common/`. Finally, run `numerai node deploy` from the `numerai_models` directory to install the package in the image, making it available to your model code.

If you want to learn more about how to customize this file [checkout the Dockerfile reference] (<https://docs.docker.com/engine/reference/builder/>).

### Cloud Components

The CLI uses [Terraform](https://www.terraform.io/) to provision cloud resources. Each component and the related cloud resource(s) are listed below. The links will take you to the AWS console where you can monitor any of these resources for a given node; just visit the link and select the resource with the same name as the node you want to monitor (further directions are given for each resource below).

- `Trigger`: A small function that schedules a "task" on your `Compute Cluster`. This "task" handles pulling the image that was created by the `Dockerfile` and running it as a `Container` on your `Compute Cluster`. This is handled by two resources:

  - **[API Gateway](https://console.aws.amazon.com/apigateway/main/apis)**:
    Hosts the webhook (HTTP endpoint) that Numerai calls to trigger your nodes.
    After clicking the link and selecting the resource, use the left sidebar to access metrics and logging.
  - **[Lambda](https://console.aws.amazon.com/lambda/home#/functions)**:
    Schedules your compute job when you call your Webhook URL.
    After clicking the link and selecting the resource, use the "Monitor" tab below the "Function Overview" section.

- `Container`: The thing that actually contains and runs your code on a computer provisioned by the `Compute Cluster`. The `--size` (or `-s`) flag on the `numerai node config` sets the CPU and Memory limits for a `Container`. This is stored in one place:

  - **[ECR (Elastic Container Repository)](https://console.aws.amazon.com/ecr/repositories)**:
    Used for storing docker images. This is the location to which `numerai docker deploy` will push your image.
    There is not much monitoring here, but you can view your images and when they were uploaded.

- `Compute Cluster`: A handler that accepts scheduled "tasks" and spins up and down computers to run `Containers`. This is handled by ECS:
  - **[ECS (Elastic Container Service)](https://console.aws.amazon.com/ecs/home#/clusters)**:
    This is where your containers will actually run and where you'll want to look if your containers don't seem to be scheduled/running.
    After clicking the link, you'll be able to scroll and monitor the top-level metrics of each cluster.
    After selecting a specific cluster, you can use the various tabs to view different components of the cluster (tasks are the runnable jobs
    that the Lambda schedules, instances are the computers the tasks run on, and metrics will show cluster-wide information)

## Special Thanks

- Thanks to [uuazed](https://github.com/uuazed) for their work on [numerapi](https://github.com/uuazed/numerapi)
- Thanks to [hellno](https://github.com/hellno) for starting the Signals [ticker map](https://github.com/hellno/numerai-signals-tickermap)
- Thanks to tit_BTCQASH ([numerai profile](https://numer.ai/tit_btcqash) and [twitter profile](https://twitter.com/tit_BTCQASH)) for debugging the environment setup process on Windows 8
- Thanks to [eses-wk](https://github.com/eses-wk) for implementing Azure support
