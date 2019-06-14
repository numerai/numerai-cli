# numerai-cli

[![CircleCI](https://circleci.com/gh/numerai/numerai-cli.svg?style=svg)](https://circleci.com/gh/numerai/numerai-cli)
[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

This is a CLI for setting up a Numerai compute node and deplying your models to it. This sets up a compute cluster in AWS (Amazon Web Services), and is architected to cost a minimal amount of money to run (on average, you will spend less than $1 per month).

![Architecture Diagram](https://github.com/numerai/numerai-cli/blob/master/docs/compute_architecture.png)

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Quickstart](#quickstart)
- [Compute Node Architecture](#compute-node-architecture)
- [Docker Example Explained](#docker-example)
- [Commands](#commands)
- [Troubleshooting](#troubleshooting)
- [Prerequisites Help](#prerequisites-help)
- [Uninstall](#uninstall)

## Prerequisites

All you need is:

1.  AWS (Amazon Web Services) account setup with an API key
2.  A Numerai API key
3.  Docker setup on your machine
4.  Python3 (your model code doesn't have to use Python3, but this CLI tool needs it)

See the [Prerequisites Help](#prerequisites-help) section if you need help getting these setup.

This project has been tested and found working on OSX, Windows 10, and Ubuntu 18.04, but should theoretically work anywhere that docker and Python are available.

## Setup

Install this library with:

```
pip3 install numerai-cli
```

## Quickstart

The following instructions will get you setup with a compute node in a matter of minutes:

```
mkdir example-numerai
cd example-numerai

numerai setup
numerai docker copy-example
numerai docker deploy
```

`numerai setup` will prompt your for AWS and Numerai API keys. Please refer to the [AWS](#aws) and [Numerai API Key](#numerai-api-key) sections for instructions on how to obtain those.

Your compute node is now setup and ready to run. Look in the `.numerai/submission_url.txt` file to see your submission url that you will provide to Numerai as your webhook url. Go to [your Numerai account](https://numer.ai/account) and select the "Compute" section to enter it there.

The default example does _not_ stake, so you will still have to manually do that every week. Alternatively, check out the bottom of predict.py for example code on how to stake automatically.

### Testing

You can test the webhook url directly like so:

```
numerai compute test-webhook
```

If the command succeeds, it will return quickly with a status of "pending". This means that your container has been scheduled to run but hasn't actually started yet.

You can check that your job has been scheduled by running:
```
numerai compute status
```

And once it's in the `RUNNING` state, you can look at the logs:
```
numerai compute logs
```

You can also check for the raw AWS logs at https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks or logs from your container at https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/fargate/service/numerai-submission

NOTE: the container takes a little time to schedule. The first time it runs also tends to take longer (2-3min), with subsequent runs starting a lot faster.

#### Local Testing

You can test your container locally by running:

```
numerai docker run
```

This will run the container exactly like it runs in the cloud. Keep in mind that this will be limited by your machine's RAM, or in the case of Windows/OSX, you can increase how much memory is allocated to docker: [Windows](https://docs.docker.com/docker-for-windows/#advanced) or [OSX](https://docs.docker.com/docker-for-mac/#advanced)

### Common Problems

#### `numerai` not in PATH

```
numerai: command not found
```

Try and run `~/.local/bin/numerai` on osx/linux or `%LOCALAPPDATA%\Programs\Python\Python37-32\Scripts\numerai.exe` on Windows.

Alternatively, exit your terminal/command prompt and re-open it. By default, pip will try to add itself to your PATH for subsequent runs, but it requires you to restart the terminal.

#### Docker not installed

```
...
subprocess.CalledProcessError: Command 'docker run --rm -it -v /home/jason/tmp/.numerai:/opt/plan -w /opt/plan hashicorp/terraform:light init' returned non-zero exit status 127.
```

If you're certain that docker is installed, make sure that your user can execute docker, ie. try to run `docker ps`. If that's the issue, then depending on your system, you can do the following:

##### Windows/OSX

Make sure the docker application is running and finished booting up. It can take a few minutes to be completely ready. When clicking on the docker tray icon, it should say "Docker Desktop is Running".

If you're using Docker Toolbox on Windows, then make sure you've opened the "Docker Quickstart Terminal".

##### Linux

```
sudo usermod -aG docker $USER
```

Then reboot or logout/login for this to take effect.

#### Wrong AWS API key

```
...
Error: error validating provider credentials: error calling sts:GetCallerIdentity: InvalidClientTokenId: The security token included in the request is invalid.
        status code: 403, request id: 32500359-7d9e-11e9-b0ed-596aba1b72c5
...
subprocess.CalledProcessError: Command 'docker run -e "AWS_ACCESS_KEY_ID=..." -e "AWS_SECRET_ACCESS_KEY=..." --rm -it -v /home/jason/tmp/.numerai:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve' returned non-zero exit status 1.
```

#### Drive not shared

If you get:

```
docker: Error response from daemon: Drive has not been shared
```

Then you need to share your drive. See https://docs.docker.com/docker-for-windows/#shared-drives for details.

## Compute Node Architecture

`numerai setup` under the hood uses [Terraform](https://www.terraform.io/) to setup an AWS environment with the following:

- An ECR (Elastic Container Repository) for storing docker containers
- A Fargate task to run your compute job in the ECS (Elastic Container Service)
- A lambda endpoint that schedules your compute job to run

There's actually a bunch of other bits of glue in AWS that are setup to run this, but these 3 are the most important. The lambda endpoint corresponds to the submission url that your provide back to Numerai. The ECR is where `numerai docker deploy` will push your image to. Fargate is where your task actually runs in the ECS, and it's where you'll want to look if things don't appear to be actually submitting.

### Submission Webhook URL

This is the url that you provide back to Numerai. It's the thing that triggers the lambda and schedules your job to run. Once you've setup the webhook in your Numerai account, it will be called Saturday morning right after a new round opens, and if your job fails (determined by not having submitted all submissions sucessfully) then it will be triggered again around 24 hours later.

## Docker example

Lets look at the docker example's files:

```
▶ tree
.
├── Dockerfile
├── model.py
├── predict.py
├── requirements.txt
└── train.py
```

### Dockerfile

And then lets look at the Dockerfile:

```
FROM python:3

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

CMD [ "python", "./predict.py" ]
```

So breaking this down line by line:

```
FROM python:3
```

This Dockerfile inherits from `python:3`, which provides us a working Python environment.

```
ADD requirements.txt .
RUN pip install -r requirements.txt
```

We then add the requirements.txt file, and pip install every requirement from it. The `ADD` keyword will take a file from your current directory and copy it over to the Docker container.

```
ADD . .
```

After that, we add everything in the current directory. This will include all of your code, as well as any other files such as serialized models that you've saved to the current directory.

```
ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY
```

These are docker aguments that `numerai train/run/deploy` will always pass into docker. They are then set in your environment, so that you can access them from your script like so:

```
import os
public_id = os.environ["NUMERAI_PUBLIC_ID"]
secret_key = os.environ["NUMERAI_SECRET_KEY"]
```

```
CMD [ "python", "./predict.py" ]
```

This sets the default command to run your docker container. This is overriden in the `numerai docker train` command, but otherwise this will be the command that is always run when using `numerai docker run` and `numerai docker deploy`

### model.py

The model code lives in here. We're using numerox, but realistically this file could host any kind of model.

### train.py

The code that gets run when running `numerai docker train`

### predict.py

The code that gets run when running `numerai docker run` and is deployed to run in the numerai compute node after executing `numerai docker deploy`

## Commands

### numerai setup

The following command will setup a full Numerai compute cluster in AWS:

```
numerai setup
```

If this is your first time running, it will also ask for your AWS and Numerai API keys. These keys are stored in $HOME/.numerai for future runs.

There will be a bunch of output about how it's setting up the AWS cluster, but the only important part is at the end:

```
...
Outputs:

docker_repo = 505651907052.dkr.ecr.us-east-1.amazonaws.com/numerai-submission
submission_url = https://wzq6vxvj8j.execute-api.us-east-1.amazonaws.com/v1/submit
```

- submission_url is your webhook url that you will provide to Numerai. Save this for later. If you forget it, a copy is stored in `.numerai/submission_url.txt`.
- docker_repo will be used in the next step but you don't need to worry about it since it's all automated for you

This command is idempotent and safe to run multiple times.

### numerai docker copy-example

If you don't have a model already setup, then you should copy over the docker example.

```
numerai docker copy-example
```

WARNING: this will overwrite the following files if they exist: Dockerfile, model.py, train.py, predict.py, and requirements.txt

There is also a more complicated example using multiple Numerai accounts:
```
numerai docker copy-example --python3-multiaccount
```
As well as using R:
```
numerai docker copy-example --rlang
```

### numerai docker train (optional, but highly recommended)

Trains your model by running `train.py`. This assumes a file called `train.py` exists and serializes your model to this directory. See the example if you want inspiration for how to do this.

```
numerai docker train
```

### numerai docker run (optional)

To test your docker container locally, you can run it with this command. This will run the default CMD for the Dockerfile, which for the default example is `predict.py`.

```
numerai docker run
```

### numerai docker deploy

Builds and pushes your docker image to the AWS docker repo

```
numerai docker deploy
```

### numerai destroy

If you ever want to delete the AWS environment to save costs or start from scratch, you can run the following:

```
numerai destroy
```

This will delete everything, including the lambda url, the docker container and associated task, as well as all the logs

This command is idempotent and safe to run multiple times.

## Troubleshooting

### Container uses up too much memory and gets killed

By default, Numerai compute nodes are limited to 8GB of RAM. If you need more, you can open up `.numerai/variables.tf` and update the `fargate_cpu` and `fargate_memory` settings to the following:

```
variable "fargate_cpu" {
  description = "Fargate instance CPU units to provision (1 vCPU = 1024 CPU units)"
  default     = "4096"
}

variable "fargate_memory" {
  description = "Fargate instance memory to provision (in MiB)"
  default     = "30720"
}
```

30720MB=30GB and is the maximum that Amazon can support.

After you've done this, re-run `numerai setup`.

Note: this will raise the costs of running your compute node, see http://fargate-pricing-calculator.site.s3-website-us-east-1.amazonaws.com/ for estimated costs. You only pay for the time it's running, rounded to the nearest minute.

### Billing Alerts

Unfortunately, there's no automated way to setup billing alerts. If you wish to be alerted when costs pass some threshold, you should follow the instructions at https://www.cloudberrylab.com/resources/blog/how-to-configure-billing-alerts-for-your-aws-account/ to setup one.

We estimate costs to be less than $5 per month unless your compute takes more than 12 hours a week. Also keep in mind that increasing the RAM/CPU as described in the previous section will increase your costs.

## Prerequisites Help

### AWS

You need to signup for AWS and create an administrative IAM user

1.  Sign up for an AWS account: https://portal.aws.amazon.com/billing/signup
2.  Create an IAM user with Administrative access: https://console.aws.amazon.com/iam/home?region=us-east-1#/users$new
    1.  Give user a name and select "Programmatic accesss"
    2.  For permissions, click "Attach existing policies directly" and click the check box next to "AdministratorAccess"
    3.  Save the "Access key ID" and "Secret access key" from the last step. You will need them later

### Numerai API Key

1.  You will need to create an API key by going to https://numer.ai/account and clicking "Add" under the "Your API keys" section.
2.  Select the following permissions for the key: "Upload submissions", "Make stakes", "View historical submission info", "View user info"
3.  Your secret key will pop up in the bottom left of the page. Copy this somewhere safe.
4.  You public ID will be listed when you click "View" under "Your API keys". Copy this somewhere safe as well.

### Python

If you don't already have Python3, you can get it from https://www.python.org/downloads/ or install it from your system's package manager.

[conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) is also a good option to get a working Python environment out of the box

### Docker

#### MacOS

If you have homebrew installed:

```
brew cask install docker
```

Otherwise you can install manually at https://hub.docker.com/editions/community/docker-ce-desktop-mac

You should also increase the RAM allocated to the VM by changing "Memory" in the following: https://docs.docker.com/docker-for-mac/#advanced

#### Windows

Install docker desktop at https://hub.docker.com/editions/community/docker-ce-desktop-windows

After you've installed docker, you _must_ enable drive sharing: https://docs.docker.com/docker-for-windows/#shared-drives

You should also increase the RAM allocated to the VM by changing "Memory" in the following: https://docs.docker.com/docker-for-windows/#advanced

##### Docker Toolbox

If your machine doesn't have Hyper-V enabled, then you will have to install docker toolbox: https://github.com/docker/toolbox/releases

After it's installed, open the "Docker QuickStart Terminal" and run the following to increase its RAM:

```
docker-machine rm default
docker-machine create -d virtualbox --virtualbox-cpu-count=2 --virtualbox-memory=4096 --virtualbox-disk-size=50000 default
```

Also note, your code must live somewhere under your User directory (ie. C:\Users\USER_NAME\ANY_FOLDER). This is a restriction of docker toolbox not sharing paths correctly otherwise.

#### Linux

Install docker through your distribution.

Ubuntu/Debian:

```
sudo apt install docker.io
```

Also make sure to add your user to the docker group:

```
sudo groupadd docker
sudo usermod -aG docker $USER
```

Then reboot or logout/login for this to take effect.

For other Linux distros, check out https://docs.docker.com/install/linux/docker-ce/centos/ and find your distro on the sidebar.

## Uninstall

Destroy the AWS environment

```
numerai destroy
```

And then uninstall the package:

```
pip3 uninstall numerai-cli
```

## Contributions

- Thanks to [uuazed](https://github.com/uuazed) for their work on [numerapi](https://github.com/uuazed/numerapi)
- Thanks to [kwgoodman](https://github.com/kwgoodman) for their work on [numerox](https://github.com/kwgoodman/numerox)
