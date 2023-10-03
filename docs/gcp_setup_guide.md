# GCP Setup Guide

Numerai CLI will create several resources in your GCP account to deploy your model. Follow the steps below to configure
your GCP account for use with the Numerai CLI.

1. Create a [Google Cloud Account](https://cloud.google.com/gcp?hl=en)
2. Make sure you are signed in to the [Google Cloud Console](https://console.cloud.google.com)
3. If you don't already have a Google Cloud project you want to use, [create a new project](https://console.cloud.google.com/projectcreate)
4. Navigate to the [Create service account](https://console.cloud.google.com/iam-admin/serviceaccounts/create) and select your project
5. Give your service account an ID and optionally a name and description, then click "Create and continue" to grant your service account access to this project.
6. Select "Basic" and then "Owner" to give your service account complete access to this project. Then select "Done".
7. You should now see your new service account in your list of service accounts. Click on your service account and then click the tab named "Keys"
8. Select "Add Key" and then click "Create a new key" in the drop down. A JSON file should be downloaded to your computer that contains this key content.
9. Record the complete path to the key you just downloaded for use in setting up the numerai-cli for GCP. (i.e. `/Users/john/Downloads/my-project-123456.json`)

[Return to main guide](../README.md#getting-started)
