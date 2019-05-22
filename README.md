# numerai-compute-cli

This is a CLI for setting up a Numer.ai compute node and deplying your models to it.

* [Prerequisites](#prerequisites)
* [Setup](#setup)
* [Uninstall](#uninstall)

## Prerequisites

All you need is:
1. Python3 (your model code doesn't have to use Python3, but this CLI tool needs it)
2. AWS (Amazon Web Services) account setup with an API key
3. Docker setup on your machine
4. A Numer.ai API key

### Python

If you don't already have Python3, you can get it from https://www.python.org/downloads/

After your python is setup, run:
```
pip install https://github.com/numerai/numerai-compute-cli/archive/master.zip
```

This will install a command named `numerai`. Test it out by running `numerai --help` in your terminal.

If your system isn't setup to add python commands to your PATH, then you can run the module directly instead with `python -m 'numerai_compute.cli'`

### AWS

You need to signup for AWS and create an administrative IAM user
1. Sign up for an AWS account
2. Create an IAM user with Administrative access: https://console.aws.amazon.com/iam/home?region=us-east-1#/users$new
    1. Give user a name and select "Programmatic accesss"
    2. For permissions, click "Attach existing policies directly" and click the check box next to "AdministratorAccess"
    3. Save the "Access key ID" and "Secret access key" from the last step. You will need them later

### Docker

#### MacOS

If you have homebrew installed:
```
brew cask install docker
```
Otherwise you can install manually at https://hub.docker.com/editions/community/docker-ce-desktop-mac

#### Windows

This project is completely untested on windows, but is meant to be cross-platform and *should* work since it only uses python and docker

Install docker desktop at https://hub.docker.com/editions/community/docker-ce-desktop-windows

#### Linux

Install docker through your distribution.

Ubuntu/Debian:
```
sudo apt install docker
```

For other Linux distros, check out https://docs.docker.com/install/linux/docker-ce/centos/ and find your distro on the sidebar.

### Numer.ai API Key

* You will need to create an API key by going to https://numer.ai/account and clicking "Add" under the "Your API keys" section.
* Select the following permissions for the key: "Upload submissions", "Make stakes", "View historical submission info", "View user info"

## Setup

Before doing anything below, make sure you have your AWS and Numer.ai API keys ready.

Install this library with:
```
pip install https://github.com/numerai/numerai-compute-cli/archive/master.zip
```

The following commands should be run from wherever your model code lives. If you would rather start from scratch, you can do:
```
mkdir example-numerai
cd example-numerai
```

### AWS setup

The following command will setup a Numer.ai compute cluster in AWS:
```
numerai setup
```

If this is your first time running, it will also ask for your AWS and Numer.ai API keys. These keys are stored in $HOME/.numerai for future runs.

There will be a bunch of output about how it's setting up the AWS cluster, but the only important part is at the end:
```
...
Outputs:

docker_repo = 505651907052.dkr.ecr.us-east-1.amazonaws.com/numerai-submission
submission_url = https://wzq6vxvj8j.execute-api.us-east-1.amazonaws.com/v1/submit
```

* submission_url is your webhook url that you will provide to Numer.ai. Save this for later. If you forget it, a copy is stored in `.numerai/submission_url.txt`.
* docker_repo will be used in the next step but you don't need to worry about it since it's all automated for you

### Copy docker example (optional)

If you don't have a docker environment already setup, then you should copy over the docker example.
```
numerai copy-docker-example
```

WARNING: this will overwrite the following files if they exist: Dockerfile, main.py, and requirements.txt

### Docker build

Build your docker image

```
numerai docker-build
```

### Docker run (optional)

To test your docker container locally, you can run it with:
```
numerai docker-run
```

### Docker deploy
Push your docker image to the AWS docker repo

```
numerai docker-deploy
```

### Test live url
You're now good to go. You can test your flow by running:
```
curl $submission_url
```
Where $submission_url is from the AWS Setup step. If you've forgotten it, you can find it by doing `cat .numerai/submission_url.txt`. If the curl succeeds, it will return immediately with a status of "pending". This means that your container has been scheduled to run but hasn't actually started yet.

You can check logs that your container actually ran at https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/fargate/service/numerai-submission or you can check for the running tasks at https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks

NOTE: the container takes a little time to schedule. The first time it runs also tends to take longer (2-3min), with subsequent runs starting a lot faster.

## Uninstall

If you ever want to delete the AWS environment to save costs or start from scratch, you can run the following:
```
numerai destroy
```

This will delete everything, including the lambda url, the docker container and associated task, as well as all the logs
