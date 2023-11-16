# AWS Setup Guide

Numerai CLI will create several resources in your AWS account to deploy your model. Follow the steps below to configure
your AWS account for use with the Numerai CLI.

If upgrading from numerai-cli 0.x, please review [Upgrading from numerai-cli v0.x](#upgrading-from-numerai-cli-v0x).

1. Create an [Amazon Web Services (AWS) Account](https://portal.aws.amazon.com/billing/signup)
2. Make sure you are signed in to the [AWS Console](console.aws.amazon.com)
3. Set up [AWS Billing](https://console.aws.amazon.com/billing/home?#/paymentmethods)
4. Create a [new IAM Policy](https://console.aws.amazon.com/iam/home?region=us-east-1#/policies$new?step=edit):
5. Select the "JSON" tab and overwrite the existing values with the following policy document:

    ```json

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "logs:*",
                    "s3:List*",
                    "ecs:*",
                    "lambda:*",
                    "ecr:*",
                    "ec2:*",
                    "iam:*",
                    "events:*",
                    "batch:*"
                ],
                "Resource": "*"
            }
        ]
    }
    ```

    NOTE: For experienced cloud users, it may seem unsafe to have `:*` next to resources. You may experiment with constricting these permissions at your own risk, but future versions of the CLI may not work if you do this.

6. Click "Next" at the bottom until you reach "Review Policy"
7. Name your policy (e.g. "compute-setup-policy") and remember this name, then hit "Create Policy"
8. Create a [new IAM User](https://us-east-1.console.aws.amazon.com/iamv2/home?region=us-east-1#/users/create)
9. Give your user a name (like "numerai-compute") and click "Next"
10. Click "Attach policies directly" and search for the policy you created in the previous steps. Click the checkbox next to your policy and click "Next" and then "Create User"
11. Click on the name of your user and then click the "Security credentials" tab. Scroll down to "Access keys", click "Create access key", click "Command Line Interface", check the confirmation box, and click "Next" and "Create access key".
12. Record the "Access key ID" and "Secret access key" from the final step.

[Return to main guide](../README.md#getting-started)


## Upgrading from numerai-cli v0.x

Additional permissions are required to upgrade from numerai-cli v0.x to numerai-cli v1.x. In numerai-cli v0.x, AWS models used API Gateway, which is no longer used in v1.x
Numerai-cli will need permissions to remove API Gateway resources from your account in order to successfully update. Replace the policy above or the policy on your current IAM User with the below policy during your upgrade:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "apigateway:*",
                "logs:*",
                "s3:List*",
                "ecs:*",
                "lambda:*",
                "ecr:*",
                "ec2:*",
                "iam:*",
                "events:*",
                "batch:*"
            ],
            "Resource": "*"
        }
    ]
}
```

After your upgrade is complete, you can remove "apigateway:\*" from your policy if desire.

