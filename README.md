# numerai-cli

[![CircleCI](https://circleci.com/gh/numerai/numerai-cli.svg?style=svg)](https://circleci.com/gh/numerai/numerai-cli)
[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

Welcome to Numerai CLI, if you haven't heard of Numerai [see our docs](https://docs.numer.ai/tournament/learn)
to learn more. Currently, this CLI configures a Numerai Prediction Node in Amazon Web Services 
(AWS) that you can deploy your models to. This solution is architected to cost less than 
$5/mo on average, but actual costs may vary. It has been tested and found working on 
MacOS/OSX, Windows 8/10, and Ubuntu 18/20, but should theoretically work anywhere that
Docker and Python 3 are available.

If you have any problems, questions, comments, concerns, or general feedback, please refer to the
[Feedback and Bug Reporting Section](#feedback-and-bug-reporting) before posting anywhere.


## Contents
- [Prerequisites](#prerequisites)
- [Node Configuration](#node-configuration)
- [Discovering Commands](#discovering-commands)
- [Troubleshooting and Feedback](#troubleshooting-and-feedback)
- [Uninstall](#uninstall)


## Prerequisites

1.  Sign up a Numerai Account, get your Numerai API Keys, and your first Model:
    1.  Sign up at https://numer.ai/signup and log in to your new account
    2.  Go to https://numer.ai/account > "Your API keys" section > click "Add"
    3.  Name your key and check all boxes under "Scope this key will have"
    4.  Enter your password and click "Confirm"
    5.  Copy your secret public key and secret key somewhere safe
  

2.  Pick a Cloud Provider and follow the directions (Currently we only support AWS):
    - [Amazon Web Services](https://github.com/numerai/numerai-cli/wiki/Amazon-Web-Services)
    

3.  Install Docker and Python for your Operating System (if you encounter errors or your
    OS is not supported, please [read the troubleshooting wiki](
    https://github.com/numerai/numerai-cli/wiki/Troubleshooting) to install Python and Docker):
    - Mac Terminal (cmd + space, type `terminal`, select `terminal.app`):
        ```
        curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-mac.sh | bash
        ```
      
    - Ubuntu 18/20 Terminal (ctrl + alt + t):
        ```
        sudo apt update && sudo apt install -y libcurl4 curl && sudo curl https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-ubu.sh | sudo bash
        ```
    
    - Windows 10 Command Prompt (windows key, type `cmd`, select Command Prompt):
        ```
        powershell -command "$Script = Invoke-WebRequest 'https://raw.githubusercontent.com/numerai/numerai-cli/master/scripts/setup-win10.ps1'; $ScriptBlock = [ScriptBlock]::Create($Script.Content); Invoke-Command -ScriptBlock $ScriptBlock"
      ```
4.  After the setup script confirms Python and Docker, install `numerai-cli` via:
    ```
    pip3 install --upgrade numerai-cli --user
    ```
    NOTES:
    - This command will also work to update to new versions of the package in the future
    - If you are using python venv then drop the --user option. 
      If you don't know what that is, disregard this note


## Node Configuration

If you know you have all the prerequisites and have your AWS and Numerai API Keys at hand,
you can run these commands to get an example node running in minutes:

```
numerai setup
numerai node config --example numerai-python3
numerai node deploy
numerai node test
```

Your compute node is now setup and ready to run. It saves important configuration 
information in `$USER_HOME/.numerai/nodes.json` including the url for your Node Trigger.
This trigger is registered with whichever model you specified during configuration.
Each trigger will be called Saturday morning right after a new round opens, 
and if the related job fails it will be triggered again around 24 hours later.

NOTES:
- The default example does _not_ make stake changes; you will still have to do that manually.
  Please refer to the [numerapi docs](https://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
  for the methods you must call to do this.
- You can view resources and logs in the AWS Console (region us-east-1) for your
  [ECS Cluster](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks)
  and [other resources](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)

For more information on Prediction Nodes, please read the
[Prediction Node Architecture wiki](https://github.com/numerai/numerai-cli/wiki/Prediction-Node-Architecture)
      

## Discovering Commands
Use the `--help` option on any command to get a full description of options and sub-commands:
```
numerai
numerai --help
numerai [command] --help
numerai [command] [sub-command] --help
```


## Troubleshooting and Feedback
Before messaging the Rocketchat channel or creating a Github issue, 
please read through the following (especially the "Troubleshooting" section in the wiki):
- [Github Wiki](https://github.com/numerai/numerai-cli/wiki)
- [Github Issues](https://github.com/numerai/numerai-cli/issues)

If you still cannot find a solution or answer, please join us on the 
[RocketChat #compute Channel](https://community.numer.ai/channel/compute) 
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
  
If you do not include this information, we cannot help you.
      

## Uninstall
```
numerai uninstall
```


## Contributions

- Thanks to [uuazed](https://github.com/uuazed) for their work on [numerapi](https://github.com/uuazed/numerapi)
- Thanks to [hellno](https://github.com/hellno) for starting the Signals [ticker map](https://github.com/hellno/numerai-signals-tickermap)
- Thanks to tit_BTCQASH ([numerai profile](https://numer.ai/tit_btcqash) and [twitter profile](https://twitter.com/tit_BTCQASH)) for debugging the environment setup process on Windows 8
