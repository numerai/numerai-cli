# numerai-cli

[![CircleCI](https://circleci.com/gh/numerai/numerai-cli.svg?style=svg)](https://circleci.com/gh/numerai/numerai-cli)
[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

CLI to set up a Numerai Compute node in AWS (Amazon Web Services) and deploy your models to it. 
This solution is architected to cost less than $5/mo on average (actual costs may vary).
It has been tested and found working on MacOS/OSX, Windows 10, and Ubuntu 18.04, 
but should theoretically work anywhere that Docker and Python 3 are available.

## IMPORTANT
If you have other questions or feedback, please join us on the 
[RocketChat #compute Channel](https://community.numer.ai/channel/compute).
Before posting a messaging the Rocketchat channel or creating a Github issue, please read through the following:
- [Github Wiki](https://github.com/numerai/numerai-cli/wiki)
- [Github Issues](https://github.com/numerai/numerai-cli/issues)

If you still cannot find a solution or answer, include the following information with your issue/message:

- The command you ran that caused the error
- Version from running `pip3 show numerai-cli`
- System Information from running
    - Mac: `system_profiler SPSoftwareDataType && system_profiler SPHardwareDataType`
    - Linux: `lsb_release -a && uname -a`
    - Windows: `powershell -command "Get-ComputerInfo"`
  
If you do not include this information, we cannot help you.


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
3.  AWS Access Keys (See [the wiki](https://github.com/numerai/numerai-cli/wiki/Prerequisites-Help) for detailed instructions)
4.  [Numerai API Keys](https://numer.ai/account)
5.  Python and Docker (see [Environment Setup](#environment-setup))

Our friend Arbitrage created [this tutorial](https://www.youtube.com/watch?v=YFgXMpQszpM&feature=youtu.be)
to help you get set up with your AWS/Numerai API Keys


## Environment Setup

For your convenience, we've included setup scripts in the `scripts` directory that will ensure the prerequisites are installed.
You can download and run the setup script for your OS with one of the following commands:

- Mac Terminal (cmd + space, type `terminal`, select `terminal.app`):
    ```
    curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-mac.sh | bash
    ```

- Ubuntu Terminal (ctrl + alt + t):
    ```
    sudo apt update && sudo apt install -y libcurl4 curl && sudo curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-ubu.sh | sudo bash
    ```

- Windows Command Prompt (windows key, type `cmd`, select Command Prompt):
    ```
    powershell -command "$Script = Invoke-WebRequest 'https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-win10.ps1'; $ScriptBlock = [ScriptBlock]::Create($Script.Content); Invoke-Command -ScriptBlock $ScriptBlock"
    ```
If you run into issues running one of these scripts, please report immediately to [RocketChat Compute Channel](https://community.numer.ai/channel/compute).


After the setup script confirms Python and Docker, install `numerai-cli` via:
```
pip3 install numerai-cli
```


## Quickstart

If you know you have all the prerequisites and have your [AWS](#aws) and [Numerai](#numerai-api-key) API Keys at hand,
you can run these commands to get the example node running in minutes:

```
mkdir example-numerai
cd example-numerai

numerai config node
numerai docker copy-example
numerai docker deploy
```

Your compute node is now setup and ready to run. It saves your configuration in `$USER_HOME/.numerai/nodes.json` that triggers your docker container. 
You can configure [your Numerai account](https://numer.ai/account) to use this webhook by entering it in the "Compute" section.
It will be called Saturday morning right after a new round opens, and if your job fails (one or more models have not submitted successfully) 
then it will be triggered again around 24 hours later.

NOTE: The default example does _not_ make stake changes; you will still have to do that manually.
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
- Thanks to [hellno](https://github.com/hellno) for starting the [ticker map](https://github.com/hellno/numerai-signals-tickermap)