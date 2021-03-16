import boto3
import numerapi

from cli.src.constants import *
from cli.src.util.debug import exception_with_msg
from cli.src.util.files import load_or_init_keys, load_or_init_nodes, store_config


def get_numerai_keys():
    keys = load_or_init_keys()
    try:
        return keys['numerai']['NUMERAI_PUBLIC_ID'],\
               keys['numerai']['NUMERAI_SECRET_KEY']
    except KeyError:
        return None, None


def config_numerai_keys():
    numerai_public, numerai_secret = get_numerai_keys()
    numerai_public = click.prompt(f'NUMERAI_PUBLIC_ID', default=numerai_public).strip()
    numerai_secret = click.prompt(f'NUMERAI_SECRET_KEY', default=numerai_secret).strip()
    check_numerai_validity(numerai_public, numerai_secret)

    keys_config = load_or_init_keys()
    keys_config.setdefault('numerai', {})
    keys_config['numerai']['NUMERAI_PUBLIC_ID'] = numerai_public
    keys_config['numerai']['NUMERAI_SECRET_KEY'] = numerai_secret
    store_config(KEYS_PATH, keys_config)


def check_numerai_validity(key_id, secret):
    try:
        napi = numerapi.NumerAPI(key_id, secret)
        napi.get_account()
    except Exception:
        raise exception_with_msg("Numerai keys seem to be invalid. "
                                 "Make sure you've entered them correctly.")


def get_provider_keys(node):
    provider = load_or_init_nodes(node)['provider']
    return load_or_init_keys(provider)


def get_aws_keys():
    keys = load_or_init_keys()
    try:
        return keys['aws']['AWS_ACCESS_KEY_ID'],\
               keys['aws']['AWS_SECRET_ACCESS_KEY']
    except KeyError:
        return None, None


def config_aws_keys():
    aws_public, aws_secret = get_aws_keys()
    aws_public = click.prompt(f'AWS_ACCESS_KEY_ID', default=aws_public).strip()
    aws_secret = click.prompt(f'AWS_SECRET_ACCESS_KEY', default=aws_secret).strip()
    check_aws_validity(aws_public, aws_secret)

    keys_config = load_or_init_keys()
    keys_config.setdefault('aws', {})
    keys_config['aws']['AWS_ACCESS_KEY_ID'] = aws_public
    keys_config['aws']['AWS_SECRET_ACCESS_KEY'] = aws_secret
    store_config(KEYS_PATH, keys_config)


def check_aws_validity(key_id, secret):
    try:
        client = boto3.client('s3', aws_access_key_id=key_id, aws_secret_access_key=secret)
        client.list_buckets()
    except Exception as e:
        if 'NotSignedUp' in str(e):
            raise exception_with_msg(
                f"Your AWS keys are valid, but the account is not finished signing up. "
                f"You either need to update your credit card in AWS at "
                f"https://portal.aws.amazon.com/billing/signup?type=resubscribe#/resubscribed, "
                f"or wait up to 24 hours for their verification process to complete."
            )

        raise exception_with_msg(
            f"AWS keys seem to be invalid. Make sure you've entered them correctly "
            f"and that your user has the necessary permissions "
            f"(see https://github.com/numerai/numerai-cli/wiki/Prerequisites-Help)."
        )


def config_provider_keys(cloud_provider):
    if cloud_provider == PROVIDER_AWS:
        config_aws_keys()


def sanitize_message(message):
    aws_public, aws_secret = get_aws_keys()
    numerai_public, numerai_secret = get_numerai_keys()
    return message.replace(aws_public, '...')\
                  .replace(aws_secret, '...')\
                  .replace(numerai_public, '...')\
                  .replace(numerai_secret, '...')
