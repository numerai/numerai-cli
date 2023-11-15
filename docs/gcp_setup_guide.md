# GCP Setup Guide

Numerai CLI will create several resources in your GCP account to deploy your model. Follow the steps below to configure
your GCP account for use with the Numerai CLI.

1. Create a [Google Cloud Account](https://cloud.google.com/gcp?hl=en)
2. Make sure you are signed in to the [Google Cloud Console](https://console.cloud.google.com)
3. Set up a [GCP Billing Account](https://console.cloud.google.com/billing/create)
4. If you don't already have a Google Cloud project you want to use, [create a new project](https://console.cloud.google.com/projectcreate)
5. Wait for the project to finish creating then ensure it's selected in the dropdown at the top of the console.
6. Ensure your billing account is assigned to your new project by checking [billing projects](https://console.cloud.google.com/billing/projects).
7. Navigate to the [Create service account](https://console.cloud.google.com/iam-admin/serviceaccounts/create)
8. Give your service account an ID and optionally a name and description, then click "Create and continue" to grant your service account access to this project.
9. Select "Basic" and then "Owner" to give your service account complete access to this project. Then select "Done".
10. You should now see your new service account in your list of service accounts. Click on your service account and then click the tab named "Keys"
11. Select "Add Key" and then click "Create a new key" in the drop down. A JSON file should be downloaded to your computer that contains this key content.
12. Record the complete path to the key you just downloaded for use in setting up the numerai-cli for GCP. (i.e. `/Users/john/Downloads/my-project-123456.json`)

[Return to main guide](../README.md#getting-started)
