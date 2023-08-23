# AWS Setup Guide

Numerai CLI will create several resources in your AWS account to deploy your model. Follow the steps below to configure
your AWS account for use with the Numerai CLI.

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
                    "apigateway:*",
                    "logs:*",
                    "s3:List*",
                    "ecs:*",
                    "lambda:*",
                    "ecr:*",
                    "ec2:*",
                    "iam:*",
                    "events:*"
                ],
                "Resource": "*"
            }
        ]
    }
    ```

    NOTE: For experienced cloud users, it may seem unsafe to have `:*` next to resources. You may experiment with constricting these permissions at your own risk, but future versions of the CLI may not work if you do this.

6. Click "Next" at the bottom until you reach "Review Policy"
7. Name your policy (e.g. "compute-setup-policy") and remember this name, then hit "Create Policy"
8. Give the user a name (like "numerai-compute") and select "Programmatic access"
9. For permissions, click "Attach existing policies directly"
10. Search for the Policy you just created and check the box next to it
11. Continue through remaining pages and click "Create User"
12. Record the "Access key ID" and "Secret access key" from the final step.
