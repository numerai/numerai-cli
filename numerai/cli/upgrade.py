import json
import shutil

import click

from numerai.cli.constants import *
from numerai.cli.util.docker import terraform
from numerai.cli.util.files import copy_files, store_config, copy_file, move_files
from numerai.cli.util.keys import (
    load_or_init_keys,
    load_or_init_nodes,
    config_numerai_keys,
    config_provider_keys,
)


# TODO: to add support for upgrade from 0.3 -> 0.4 Azure provider version


@click.command()
@click.option("--verbose", "-v", is_flag=True)
def upgrade(verbose):
    """
    Upgrades configuration from <=0.2 format to >=0.3 format.
    """
    home = str(Path.home())
    old_key_path = os.path.join(home, ".numerai")
    old_config_path = os.path.join(os.getcwd(), ".numerai/")

    click.secho(str(old_key_path))
    click.secho(str(old_config_path))

    if str(old_key_path) == str(old_config_path):
        click.secho("You cannot run this command from your home directory.")
        return

    if not os.path.exists(old_config_path):
        click.secho(
            "Run this command from the directory in which you first ran `numerai setup`"
            " for CLI version 0.1 and 0.2 (it should have the .numerai folder in it)."
            " If instead you're trying to upgrade from 0.3 to 0.4,"
            " then run this in your home directory."
        )
        return

    click.secho(
        f"Upgrading, do not interrupt or else " f"your environment may be corrupted.",
        fg="yellow",
    )

    # MOVE KEYS FILE
    if os.path.isfile(old_key_path):
        temp_key_path = os.path.join(old_config_path, ".keys")
        click.secho(
            f"\tmoving old keyfile from '{old_key_path}' to '{temp_key_path}'",
        )
        shutil.move(old_key_path, temp_key_path)

    # MOVE CONFIG FILE
    if os.path.exists(old_config_path):
        click.secho(
            f"\tmoving old config from {old_config_path} to {CONFIG_PATH}",
        )
        shutil.move(old_config_path, CONFIG_PATH)

    # INIT KEYS AND NODES
    keys_config = load_or_init_keys()
    supported_providers = ["aws", "azure"]
    if (
        not os.path.exists(KEYS_PATH)
        or "numerai" not in keys_config
        or not any(
            [provider for provider in keys_config if provider in supported_providers]
        )
    ):
        click.secho(f"Keys missing from {KEYS_PATH}, you must re-initialize your keys:")
        config_numerai_keys()
        click.secho(f"Currently supported providers: {supported_providers}")
        provider = click.prompt("Enter your provider:", default="aws")
        if provider == "aws":
            config_provider_keys(PROVIDER_AWS)
        elif provider == "azure":
            config_provider_keys(PROVIDER_AZURE)
        else:
            click.secho(f"Invalid provider: {provider}", fg="red")
            exit(1)
    # nodes_config = load_or_init_nodes()

    # DELETE OLD CONFIG FILES
    click.secho("Checking for old config output files...", fg="yellow")
    old_suburl_path = os.path.join(CONFIG_PATH, "submission_url.txt")
    if os.path.exists(old_suburl_path):
        click.secho(
            f"\tdeleting {old_suburl_path}, you can populate the "
            f"new nodes.json file with `numerai node config`"
        )
        os.remove(old_suburl_path)
    old_docker_path = os.path.join(CONFIG_PATH, "docker_repo.txt")
    if os.path.exists(old_docker_path):
        click.secho(
            f"\tdeleting {old_docker_path}, you can populate the "
            f"new nodes.json file with `numerai node config`"
        )
        os.remove(old_docker_path)

    # Upgrade to 0.4
    # create "/aws" directory, then copy all of the old config over (except .keys and nodes.json)
    if not os.path.isdir(os.path.join(CONFIG_PATH, "azure")):
        click.secho("Upgrading from 0.3 to 0.4...", fg="yellow")
        # Create the temp folder if it doesn't exist already
        temp_folder_path = os.path.join(CONFIG_PATH, "temp")
        if not os.path.exists(temp_folder_path):
            os.makedirs(temp_folder_path)
        else:
            click.secho(
                f"Temp folder {temp_folder_path} already exists, "
                f"upgrading will remove everything in this folder. "
                f"Please save a copy elsewhere and retry 'numerai upgrade'",
                fg="red",
            )
            exit(1)

        # Move all files and folders in the config folder to the temp folder
        move_files(CONFIG_PATH, temp_folder_path)

        # Move .keys and nodes.json back to the config folder
        unchange_files = [".keys", "nodes.json"]
        for file in unchange_files:
            try:
                src_path = os.path.join(temp_folder_path, file)
                dst_path = os.path.join(CONFIG_PATH, file)
                shutil.move(src_path, dst_path)
                click.secho(f"Move {src_path} to {dst_path}")

            except FileNotFoundError:
                click.secho(f"File {file} not found in {temp_folder_path}", fg="yellow")

        # Create /aws directory
        aws_path = os.path.join(CONFIG_PATH, "aws")
        if not os.path.exists(aws_path):
            os.makedirs(aws_path)

        # Move all files and folders from the temp folder to the aws folder
        move_files(temp_folder_path, aws_path)
        os.rmdir(temp_folder_path)

    # UPGRADE, RENAME, AND UPDATE TERRAFORM FILES
    click.secho("Upgrading terraform files...", fg="yellow")
    try:
        with open(os.path.join(CONFIG_PATH, "aws", "terraform.tfstate")) as f:
            tfstate = json.load(f)
        keys_config = load_or_init_keys("aws")
        if "0.12" in tfstate["terraform_version"]:
            terraform(
                "0.13upgrade -yes ",
                verbose,
                provider="aws",
                version="0.13.6",
                env_vars=keys_config,
            )
            terraform(
                "init", verbose, provider="aws", version="0.13.6", env_vars=keys_config
            )
            terraform(
                "apply -auto-approve",
                verbose,
                provider="aws",
                version="0.13.6",
                env_vars=keys_config,
            )
    except FileNotFoundError:
        pass
    except click.ClickException:
        click.secho("Failed to upgrade to terraform state!", fg="red")
        return
    except Exception as e:
        click.secho(f"Uncaught exception: {str(e)}", fg="red")
        return

    # Rename terraform files, only for v0.2 -> v0.3 upgrade
    try:
        tf_files_map = {
            "main.tf": "-main.tf",
            "variables.tf": "-inputs.tf",
            "outputs.tf": "-outputs.tf",
        }
        for old_file, new_file in tf_files_map.items():
            old_file = os.path.join(CONFIG_PATH, old_file)
            new_file = os.path.join(CONFIG_PATH, "aws", new_file)
            if os.path.exists(new_file):
                os.remove(new_file)
            if not os.path.exists(old_file):
                click.secho(
                    f"\trenaming and moving {old_file} to {new_file} to prep for upgrade..."
                )
                shutil.move(old_file, new_file)
            else:
                os.remove(old_file)
    except FileNotFoundError:
        pass
    copy_files(TERRAFORM_PATH, CONFIG_PATH, force=True, verbose=verbose)

    # terraform init
    click.secho("Re-initializing terraform...", fg="yellow")
    terraform("init -upgrade", verbose=verbose, provider="aws")

    if click.confirm(
        "It's recommended you destroy your current Compute Node. Continue?"
    ):
        click.secho("Removing old cloud infrastructure...", fg="yellow")
        nodes_config = load_or_init_nodes()
        store_config(NODES_PATH, nodes_config)
        copy_file(NODES_PATH, f"{CONFIG_PATH}/aws/", force=True, verbose=True)
        terraform(
            "destroy -auto-approve",
            verbose,
            provider="aws",
            env_vars=load_or_init_keys("aws"),
            inputs={"node_config_file": "nodes.json"},
        )

    click.secho("Upgrade complete!", fg="green")
    click.secho(
        "run `numerai node config --help` to learn how to "
        "register this directory as a prediction node"
    )
