# Azure Setup Guide

Numerai CLI will create several resources in your Azure account to deploy and run your models.
Follow the steps below to give the Numerai CLI access to your Azure account.

1. Create an [Azure Account](https://signup.azure.com)
2. Make sure you are signed in to the [Azure Portal](https://portal.azure.com/)
3. Create an [Azure Subscription](https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade). Save your `Subscription ID` to use in the Numerai CLI later.
4. In `Azure Active Directory`, navigate to [App Registrations](https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps)
5. Create a `New Registration` from the `App Registrations` blade. Give your application a name and leave the other options as default.
6. Creating a new registration will take you to your app's details page. If it doesn't, navigate back to your [App Registrations](https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps) and select your application from the `All Applications` list. From the `Overview` page, save your application's `Application (client) ID` and `Directory (tenant) ID` for setting up Numerai CLI later.
7. Next we will create a new client secret. Navigate to `Certificates & secrets` from the menu on the left. Select `Client secrets` and click `Create new client secret`
8. Give your secret any name. Once it is created, copy the `value` of your secret to your clipboard and save this value for setting up Numerai CLI later.
9. We need to give your app access to your subscription. Navigate back to [Subscriptions](https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade) and select the subscription you created earlier.
10. Select `Access control (IAM)` from the menu on the left, click `+ Add`, and from the drop down menu select `Add role assignment`. Under `Role`, select `Privileged administrator roles`, and then `Owner`.
11. Next we will assign Owner permissions to your app. Select `Members` and then click `+ Select members`. In the search box, type the name of the app you created earlier and hit the return key. When your app appears, select your app and then click the `Select` button at the bottom of the screen. Finally, click `Review and assign`.

[Return to main guide](../README.md#getting-started)
