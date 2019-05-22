# numerai-compute-cli

It's not much of a CLI yet, but the skeleton is ready to go:

* [Prerequisites](#prerequisites)
* [Setup](#setup)
* [Uninstall](#uninstall)

## Prerequisites

All you need is:
1. Python3 (your model doesn't have to use Python3, but this CLI tool needs it)
1b. Install the aws cli, `pip install awscli`
2. AWS (Amazon Web Services) account setup
3. Docker setup on your machine


### Python

If you don't already have Python3, you can get it from https://www.python.org/downloads/

### AWS

You need to signup for AWS and create an administrative IAM user
1. Sign up for an AWS account:

TODO

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

## Setup

Before doing anything below, you need to add your AWS key and numerai key to your environment variables:
```
export NUMERAI_PUBLIC_ID=...
export NUMERAI_SECRET_KEY=...
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### AWS setup

1. Setup your AWS Lambda and ECS task:
```
docker run -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" --rm -it -v $(pwd)/terraform:/opt/plan -w /opt/plan hashicorp/terraform:light apply -auto-approve
```

Note the output block from this command, e.g.:
```
...
Outputs:

docker_repo = 505651907052.dkr.ecr.us-east-1.amazonaws.com/numerai-submission
submission_url = https://wzq6vxvj8j.execute-api.us-east-1.amazonaws.com/v1/submit
```

docker_repo will be used in the next step, and submission_url is your webhook url that you will provide to Numer.ai. Set docker_repo and submission_url in your env for ease of use later:
```
export docker_repo=505651907052.dkr.ecr.us-east-1.amazonaws.com/numerai-submission
export submission_url=https://wzq6vxvj8j.execute-api.us-east-1.amazonaws.com/v1/submit
```

### Docker build

1. Login to the AWS secure docker repo:
```
$(aws ecr get-login --region us-east-1 --no-include-email)
```

That command looks weird, but just paste it exactly as-is into your terminal. If you're paranoid, you can `echo` it out first to see the `docker login` command that it generates.

2. Build your docker image

Use $docker_repo from above
```
docker build -t $docker_repo --build-arg NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID --build-arg NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY .
```

2b. (optional) Run the docker image locally:
```
docker run $docker_repo
```

3.
```
docker push $docker_repo
```

You're now good to go. You can test your flow by running:
```
curl $submission_url
```
Where $submission_url is from the AWS Setup step. The curl will return immediately, with a status of "pending". This means that your container has been scheduled to run but hasn't actually started yet.

You can check logs that your container actually ran at https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:group=/fargate/service/numerai-submission or you can check for the running tasks at https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks

NOTE: the container takes a little time to schedule. The first time it runs also tends to take longer (2-3min), with subsequent runs starting a lot faster.

## Uninstall

If you ever want to delete the AWS environment to save costs or start from scratch, you can run the following:
```
docker run -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" --rm -it -v $(pwd)/terraform:/opt/plan -w /opt/plan hashicorp/terraform:light destroy -auto-approve
```

This will delete everything, including the lambda url, the docker container and associated task, as well as all the logs
