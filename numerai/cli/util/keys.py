import json
from configparser import ConfigParser, MissingSectionHeaderError

import boto3
import click
import shutil
import numerapi


from azure.identity import ClientSecretCredential  # DefaultAzureCredential
from azure.mgmt.subscription import SubscriptionClient

from google.oauth2 import service_account
from google.cloud import storage



from numerai.cli.constants import *
from numerai.cli.constants import KEYS_PATH
from numerai.cli.util.debug import exception_with_msg
from numerai.cli.util.files import (
    load_or_init_nodes,
    store_config,
    maybe_create,
    load_config
)


def reformat_keys():
    # REFORMAT OLD KEYS
    try:
        config = ConfigParser()
        config.read(KEYS_PATH)
        click.secho(f"Old keyfile format found, reformatting...", fg="yellow")

        new_config = {
            "aws": {
                "AWS_ACCESS_KEY_ID": config["default"]["AWS_ACCESS_KEY_ID"],
                "AWS_SECRET_ACCESS_KEY": config["default"]["AWS_SECRET_ACCESS_KEY"],
            },
            "numerai": {
                "NUMERAI_PUBLIC_ID": config["default"]["NUMERAI_PUBLIC_ID"],
                "NUMERAI_SECRET_KEY": config["default"]["NUMERAI_SECRET_KEY"],
            },
        }

        del config["default"]
        with open(os.open(KEYS_PATH, os.O_CREAT | os.O_WRONLY, 0o600), "w") as f:
            config.write(f)
            json.dump(new_config, f, indent=2)

    # if this file is already a json file skip
    except MissingSectionHeaderError:
        pass


def load_or_init_keys(provider=None):
    maybe_create(KEYS_PATH, protected=True)
    try:
        cfg = load_config(KEYS_PATH)
    except json.decoder.JSONDecodeError as e:
        reformat_keys()
        cfg = load_config(KEYS_PATH)
    if provider:
        return cfg[provider]
    return cfg


def get_numerai_keys():
    keys = load_or_init_keys()
    try:
        return (
            keys["numerai"]["NUMERAI_PUBLIC_ID"],
            keys["numerai"]["NUMERAI_SECRET_KEY"],
        )
    except KeyError:
        return None, None


def prompt_for_key(name, default):
    hidden = sanitize_message(default)
    new = click.prompt(name, default=hidden).strip()
    if new == hidden:
        return default
    return new


def config_numerai_keys():
    numerai_public, numerai_secret = get_numerai_keys()

    numerai_public = prompt_for_key("NUMERAI_PUBLIC_ID", numerai_public)
    numerai_secret = prompt_for_key("NUMERAI_SECRET_KEY", numerai_secret)
    check_numerai_validity(numerai_public, numerai_secret)

    keys_config = load_or_init_keys()
    keys_config.setdefault("numerai", {})
    keys_config["numerai"]["NUMERAI_PUBLIC_ID"] = numerai_public
    keys_config["numerai"]["NUMERAI_SECRET_KEY"] = numerai_secret
    store_config(KEYS_PATH, keys_config)


def check_numerai_validity(key_id, secret):
    try:
        napi = numerapi.NumerAPI(key_id, secret)
        napi.get_account()
    except Exception:
        raise exception_with_msg(
            "Numerai keys seem to be invalid. "
            "Make sure you've entered them correctly."
        )


def get_provider_keys(node):
    provider = load_or_init_nodes(node)["provider"]
    return load_or_init_keys(provider)


def get_aws_keys():
    keys = load_or_init_keys()
    try:
        return keys["aws"]["AWS_ACCESS_KEY_ID"], keys["aws"]["AWS_SECRET_ACCESS_KEY"]
    except KeyError:
        return None, None


def get_azure_keys():
    keys = load_or_init_keys()
    try:
        return (
            keys["azure"]["ARM_SUBSCRIPTION_ID"],
            keys["azure"]["ARM_CLIENT_ID"],
            keys["azure"]["ARM_TENANT_ID"],
            keys["azure"]["ARM_CLIENT_SECRET"],
        )

    except KeyError:
        return None, None, None, None

def get_gcp_keys():
    keys = load_or_init_keys()
    try:
        return (
            keys["gcp"]["GCP_KEYS_PATH"]
        )
    except KeyError:
        return None

def config_aws_keys():
    aws_public, aws_secret = get_aws_keys()
    aws_public = prompt_for_key("AWS_ACCESS_KEY_ID", aws_public)
    aws_secret = prompt_for_key("AWS_SECRET_ACCESS_KEY", aws_secret)
    check_aws_validity(aws_public, aws_secret)

    keys_config = load_or_init_keys()
    keys_config.setdefault("aws", {})
    keys_config["aws"]["AWS_ACCESS_KEY_ID"] = aws_public
    keys_config["aws"]["AWS_SECRET_ACCESS_KEY"] = aws_secret
    store_config(KEYS_PATH, keys_config)


def config_azure_keys():
    azure_subs_id, azure_client, azure_tenant, azure_secret = get_azure_keys()
    azure_subs_id = prompt_for_key(
        "Azure Subscription ID [ARM_SUBSCRIPTION_ID]", azure_subs_id
    )
    azure_client = prompt_for_key("Azure Client ID [ARM_CLIENT_ID]", azure_client)
    azure_tenant = prompt_for_key("Azure Tenant ID [ARM_TENANT_ID]", azure_tenant)
    azure_secret = prompt_for_key(
        "Azure Client Secret [ARM_CLIENT_SECRET]", azure_secret
    )
    check_azure_validity(azure_subs_id, azure_client, azure_tenant, azure_secret)

    keys_config = load_or_init_keys()
    keys_config.setdefault("azure", {})
    # Renaming the keys to match the environment variables that TF would recognize
    # https://developer.hashicorp.com/terraform/language/settings/backends/azurerm#environment
    keys_config["azure"]["ARM_SUBSCRIPTION_ID"] = azure_subs_id
    keys_config["azure"]["ARM_CLIENT_ID"] = azure_client
    keys_config["azure"]["ARM_TENANT_ID"] = azure_tenant
    keys_config["azure"]["ARM_CLIENT_SECRET"] = azure_secret
    store_config(KEYS_PATH, keys_config)

def config_gcp_keys():
    gcp_keys_path = get_gcp_keys()
    gcp_keys_path_new = prompt_for_key(f"Path to GCP keys file (will be copied to {GCP_KEYS_PATH})", gcp_keys_path)
    if gcp_keys_path_new != gcp_keys_path:
        shutil.copy(gcp_keys_path_new, GCP_KEYS_PATH)

    check_gcp_validity()

    keys_config = load_or_init_keys()
    keys_config.setdefault("gcp", {})
    keys_config["gcp"]["GCP_KEYS_PATH"] = GCP_KEYS_PATH
    store_config(KEYS_PATH, keys_config)


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client(
            "s3", aws_access_key_id=key_id, aws_secret_access_key=secret
        )
        client.list_buckets()
    except Exception as e:
        if "NotSignedUp" in str(e):
            raise exception_with_msg(
                f"Your AWS keys are valid, but the account is not finished signing up. "
                f"You either need to update your credit card in AWS at "
                f"https://portal.aws.amazon.com/billing/signup?type=resubscribe#/resubscribed, "
                f"or wait up to 24 hours for their verification process to complete."
            )

        raise exception_with_msg(
            f"AWS keys seem to be invalid. Make sure you've entered them correctly "
            f"and that your user has the necessary permissions (for help, see "
            f"https://github.com/numerai/numerai-cli/wiki/Amazon-Web-Services)."
        )

def check_azure_validity(subs_id, client_id, tenant_id, secret):
    try:
        credentials = ClientSecretCredential(
            client_id=client_id, tenant_id=tenant_id, client_secret=secret
        )
        sub_client = SubscriptionClient(credentials)
        subs = [sub.as_dict() for sub in sub_client.subscriptions.list()]
        all_subs_ids = [subs_details["subscription_id"] for subs_details in subs]
        if subs_id not in all_subs_ids:
            raise Exception("Invalid Subscription ID")

    except Exception as e:
        error_msg = (
            f"Make sure you follow the instructions in the wiki page: "
            + f"https://github.com/numerai/numerai-cli/blob/master/docs/azure_setup_guide.md"
            + f"to set up the Client ID, Tenant ID and Client Secret correctly."
        )
        if "AADSTS700016" in str(e):
            raise exception_with_msg(f"Invalid Client ID. " + error_msg)
        elif "double check your tenant name" in str(e):
            raise exception_with_msg(f"Invalid Tenant ID. " + error_msg)
        elif "Invalid client secret" in str(e):
            raise exception_with_msg(f"Invalid Client Secret. " + error_msg)
        elif "Invalid Subscription ID" in str(e):
            raise exception_with_msg(
                f"Azure Subscription ID is invalid, or IAM is NOT set up correctly. "
                + f"Your Azure Client ID, Tenant ID and Client Secret are valid. "
                + f"Make sure to follow the instructions in the wiki page: "
                + f"https://github.com/numerai/numerai-cli/blob/master/docs/azure_setup_guide.md"
            )

def check_gcp_validity():
    try:
        credentials = service_account.Credentials.from_service_account_file(GCP_KEYS_PATH)
        client = storage.Client(credentials=credentials)
        response = client.list_buckets()
        print(response)
    except Exception as e:
        error_msg = (
            f"Make sure you follow the instructions in the wiki page: "
            + f"https://github.com/numerai/numerai-cli/blob/master/docs/gcp_setup_guide.md"
            + f"to set up the keys file correctly."
        )
        if "Request had invalid authentication credentials." in str(e):
            raise exception_with_msg(f"Invalid credentials. " + error_msg)
        else:
            raise e


def config_provider_keys(cloud_provider):
    if cloud_provider == PROVIDER_AWS:
        config_aws_keys()
    elif cloud_provider == PROVIDER_AZURE:
        config_azure_keys()
    elif cloud_provider == PROVIDER_GCP:
        config_gcp_keys()


def sanitize_message(message, censor_substr=None):
    if message is None:
        return None
    all_keys = get_aws_keys() + get_numerai_keys() + get_azure_keys()
    for key in all_keys:
        if key:
            try:
                message = message.replace(key, f"...{key[-5:]}")
            except AttributeError:
                continue
    if censor_substr:
        message = message.replace(censor_substr, f"...{censor_substr[-5:]}")
    return message
