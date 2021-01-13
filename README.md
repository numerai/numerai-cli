# numerai-cli

[![CircleCI](https://circleci.com/gh/numerai/numerai-cli.svg?style=svg)](https://circleci.com/gh/numerai/numerai-cli)
[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

CLI to set up a Numerai Compute node in AWS (Amazon Web Services) and deploy your models to it. 
This is architected to cost a minimal amount of money to run (less than $5 per month on average).
It has been tested and found working on MacOS/OSX, Windows 10, and Ubuntu 18.04, 
but should theoretically work anywhere that docker and Python are available.

## IMPORTANT
This tool continually improves with your help. As more users interact with it, more bugs will be found and fixed.
If you have questions or feedback, please join us on the [RocketChat Compute Channel](https://community.numer.ai/channel/compute).
If you run into an error, please read the [Wiki](https://github.com/numerai/numerai-cli/wiki) and search [Github issues](https://github.com/numerai/numerai-cli/issues)
before posting on Github/Rocketchat, this way we can focus on unsolved errors first. If you must post an error for more help,
run these commands and include information from each:
- Version from `pip3 show numerai-cli`
- System Information from
    - Mac: `system_profiler SPSoftwareDataType && system_profiler SPHardwareDataType`
    - Linux: `lsb_release -a && uname -a`
    - Windows: `powershell -command "Get-ComputerInfo`

## Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Quickstart](#quickstart)
- [Testing](#testing)
- [Commands](#commands)
- [Uninstall](#uninstall)


## Prerequisites
1.  An [AWS (Amazon Web Services) Account](https://portal.aws.amazon.com/billing/signup)
2.  AWS [Billing set up](https://console.aws.amazon.com/billing/home?#/paymentmethods)
2.  AWS [Access Keys](https://console.aws.amazon.com/iam/home?#/security_credentials)
3.  [Numerai API Keys](https://numer.ai/account)
4.  Python and Docker (see [Environment Setup](#environment-setup))


## Environment Setup

For your convenience, we've included setup scripts in the `scripts` directory that will ensure the prerequisites are installed.
You can download and run the setup script for your OS with one of the following commands:

- Mac Terminal (cmd + space, type `terminal`, select `terminal.app`):
    ```
    curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-mac.sh | bash
    ```

- Ubuntu 18 Terminal (ctrl + alt + t):
    ```
    apt update && apt install -y libcurl4 curl && curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-ubu18.sh | bash
    ```

- Windows Command Prompt (windows key, type `cmd`, select Command Prompt):
    ```
    powershell -command "$Script = Invoke-WebRequest 'https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-win10.ps1'; $ScriptBlock = [ScriptBlock]::Create($Script.Content); Invoke-Command -ScriptBlock $ScriptBlock"
    ```
  
Then, make sure python and docker are installed by running the `python` and `docker` commands.

See the [Prerequisites Help](#prerequisites-help) section if you need further help getting these setup.


After runnning the setup script and it says it found Python and Docker, install this library with:

```
pip3 install numerai-cli
```



## Quickstart

If you know you have all the prerequisites and have your [AWS](#aws) and [Numerai](#numerai-api-key) API Keys at hand,
you can run these commands to get the example application running in minutes:

```
mkdir example-numerai
cd example-numerai

numerai setup
numerai docker copy-example
numerai docker deploy
```

Your compute node is now setup and ready to run. It saves the webhook URL in `.numerai/submission_url.txt` that triggers your docker container. 
You can configure [your Numerai account](https://numer.ai/account) to use this webhook by entering it in the "Compute" section.
It will be called Saturday morning right after a new round opens, and if your job fails (one ore more models have not submitted successfully) 
then it will be triggered again around 24 hours later.

NOTE: The default example does _not_ stake, so you will still have to manually do that every week.
Please refer to the [numerapi docs](https://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
for the methods you must call to do this.

## Testing

- Test webhook URL (schedule a job in the cloud):   
  `numerai compute test-webhook`
  

- Check your job status:    
  `numerai compute status`
  

- View logs for "RUNNING" Job:  
  `numerai compute logs`


- You can test locally too:  
  `numerai docker run`


- NOTES:
    - You can also view logs in the console for your [ECS Cluster](https://console.aws.amazon.com/ecs/home?#/clusters/numerai-submission-ecs-cluster/tasks)
    and your [Container](https://console.aws.amazon.com/cloudwatch/home?#logStream:group=/fargate/service/numerai-submission)
    - Scheduling a job does not immediately run the container.
    This takes several minutes the first time it runs, with subsequent runs starting a lot faster.
      


## Commands
To get descriptions of each command available, run one of these:
```
numerai
numerai --help
numerai [command] --help
numerai [command] [sub-command] --help
```

      
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
