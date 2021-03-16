# numerai-cli

[![CircleCI](https://circleci.com/gh/numerai/numerai-cli.svg?style=svg)](https://circleci.com/gh/numerai/numerai-cli)
[![PyPI](https://img.shields.io/pypi/v/numerai-cli.svg?color=brightgreen)](https://pypi.org/project/numerai-cli/)

Welcome to Numerai CLI, if you haven't heard of numerai [see our docs](https://docs.numer.ai/tournament/learn)
to learn more. Currently this CLI configures a Numerai Prediction Node in Amazon Web Services 
(AWS) that you can deploy your models to. This solution is architected to cost less than 
$5/mo on average, but actual costs may vary. It has been tested and found working on 
MacOS/OSX, Windows 10, and Ubuntu 18.04, but should theoretically work anywhere that
Docker and Python 3 are available.

If you have any problems, questions, comments, concerns, or general feedback, please refer to the
[Feedback and Bug Reporting Section](#feedback-and-bug-reporting) before posting anywhere.


## Contents
- [Prerequisites](#prerequisites)
- [Node Configuration](#node-configuration)
- [Node Testing](#testing)
- [Listing Commands](#commands)
- [Troubleshooting and Feedback](#troubleshooting-and-feedback)
- [Uninstall](#uninstall)


## Prerequisites

1.  Sign up a Numerai Account, get your Numerai API Keys, and your first Model:
    1.  Sign up at https://numer.ai/signup and log in to your new account
    2.  Go to https://numer.ai/account > "Your API keys" section > click "Add"
    3.  Name your key and check all boxes under "Scope this key will have"
    4.  Enter your password and click "Confirm"
    5.  Copy your secret public key and secret key somewhere safe
  

3.  Pick a Cloud Provider and follow the directions (Currently we only support AWS):
    - [Amazon Web Services](https://github.com/numerai/numerai-cli/wiki/Amazon-Web-Services)
    

4.  Install Docker and Python for your Operating System:
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
5.  After the setup script confirms Python and Docker, install `numerai-cli` via:
    ```
    pip3 install numerai-cli --user
    ```
    NOTE: If you are using python venv then drop the --user option. If you don't know what that is, disregard this note

6. Finally 

## Node Configuration

If you know you have all the prerequisites and have your AWS and Numerai API Keys at hand,
you can run these commands to get an example node running in minutes:

NOTE: replace `[MODEL ID]` by going to https://numer.ai/models and copying the ID under the name of your first model.

```
numerai setup
numerai node create --example numerai-python3 --model-id [MODEL ID]
numerai node deploy
numerai node test
```

Your compute node is now setup and ready to run. It saves important configuration information in `$USER_HOME/.numerai/nodes.json`
including the url for your Node Trigger. This trigger is registered with whichever model you specified during configuration.
Each trigger will be called Saturday morning right after a new round opens, and if the related job fails it will be triggered again around 24 hours later.

NOTE: The default example does _not_ make stake changes; you will still have to do that manually.
Please refer to the [numerapi docs](https://numerapi.readthedocs.io/en/latest/api/numerapi.html#module-numerapi.numerapi)
for the methods you must call to do this.

## Node Testing

- Test webhook URL (schedule a job in the cloud):   
  `numerai compute test-webhook`
  

- Check your job status:    
  `numerai compute status`
  

- View logs for "RUNNING" Job:  
  `numerai compute logs`
  

- You can test locally too:  
  `numerai docker run`
  

- NOTES:
    - You can also view resources and logs in the AWS Console for your
      [ECS Cluster](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/numerai-submission-ecs-cluster/tasks)
      and [other resources](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)
    - Scheduling a job does not immediately run the container.
      This takes several minutes the first time it runs,
      with subsequent runs starting a lot faster.
      

## Listing Commands
Run one of these to get descriptions of each command available:
```
numerai
numerai --help
numerai [command] --help
numerai [command] [sub-command] --help
```


## Troubleshooting and Feedback
Before posting a messaging the Rocketchat channel or creating a Github issue, 
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
1. Destroy the AWS environment:
    ```
    numerai destroy
    ```

2. Uninstall the package:
    ```
    pip3 uninstall numerai-cli
    ```


## Contributions

- Thanks to [uuazed](https://github.com/uuazed) for their work on [numerapi](https://github.com/uuazed/numerapi)
- Thanks to [hellno](https://github.com/hellno) for starting the [ticker map](https://github.com/hellno/numerai-signals-tickermap)