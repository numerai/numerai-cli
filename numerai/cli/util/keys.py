import json
from configparser import \
    ConfigParser, \
    MissingSectionHeaderError

import boto3
import click
import numerapi

from numerai.cli.constants import *
from numerai.cli.constants import KEYS_PATH
from numerai.cli.util.debug import exception_with_msg
from numerai.cli.util.files import \
    load_or_init_nodes, \
    store_config, \
    maybe_create, \
    load_config


def reformat_keys():
    # REFORMAT OLD KEYS
    try:
        config = ConfigParser()
        config.read(KEYS_PATH)
        click.secho(f"Old keyfile format found, reformatting...", fg='yellow')

        new_config = {
            'aws': {
                'AWS_ACCESS_KEY_ID': config['default']['AWS_ACCESS_KEY_ID'],
                'AWS_SECRET_ACCESS_KEY': config['default']['AWS_SECRET_ACCESS_KEY']
            },
            'numerai': {
                'NUMERAI_PUBLIC_ID': config['default']['NUMERAI_PUBLIC_ID'],
                'NUMERAI_SECRET_KEY': config['default']['NUMERAI_SECRET_KEY']
            }
        }

        del config['default']
        with open(os.open(KEYS_PATH, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as f:
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
        return keys['numerai']['NUMERAI_PUBLIC_ID'],\
               keys['numerai']['NUMERAI_SECRET_KEY']
    except KeyError:
        return None, None


def config_numerai_keys():
    numerai_public, numerai_secret = get_numerai_keys()
    numerai_public = click.prompt(
        f'NUMERAI_PUBLIC_ID',
        default=sanitize_message(numerai_public)
    ).strip()
    numerai_secret = click.prompt(
        f'NUMERAI_SECRET_KEY',
        default=sanitize_message(numerai_secret)
    ).strip()
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
    aws_public = click.prompt(
        f'AWS_ACCESS_KEY_ID',
        default=sanitize_message(aws_public)
    ).strip()
    aws_secret = click.prompt(
        f'AWS_SECRET_ACCESS_KEY',
        default=sanitize_message(aws_secret)
    ).strip()
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
            f"and that your user has the necessary permissions (for help, see "
            f"https://github.com/numerai/numerai-cli/wiki/Amazon-Web-Services)."
        )


def config_provider_keys(cloud_provider):
    if cloud_provider == PROVIDER_AWS:
        config_aws_keys()


def sanitize_message(message):
    if message is None:
        return None
    all_keys = get_aws_keys() + get_numerai_keys()
    for key in all_keys:
        try:
            message = message.replace(key, f'...{key[-5:]}')
        except AttributeError:
            continue

    return message
