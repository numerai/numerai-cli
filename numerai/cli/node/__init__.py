"""Init for node"""

import json
import logging
import click

from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.node.config import config
from numerai.cli.node.deploy import deploy
from numerai.cli.node.destroy import destroy
from numerai.cli.node.test import test, status
from numerai.cli.util.keys import get_numerai_keys

# Setting azure's logging level "ERROR" to avoid spamming the terminal


def tournaments_dict():
    napi = base_api.Api()
    tournaments = napi.raw_query('query { tournaments { name tournament } }')
    return {t["tournament"]: t["name"] for t in tournaments["data"]["tournaments"]}


def get_models(tournament):
    napi = base_api.Api(*get_numerai_keys())
    models = napi.get_models(tournament)
    tournaments = napi.raw_query('query { tournaments { name tournament } }')
    name_prefix = tournaments_dict()[tournament]
    model_dict = {}
    for model_name, model_id in models.items():
        model_dict[model_name] = {
            "id": model_id,
            "name": f"{name_prefix}-{model_name}",
            "tournament": tournament,
        }
    return model_dict


@click.group()
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--model-name",
    "-m",
    type=str,
    prompt=True,
    help="The name of one of your models to configure the Prediction Node for."
    " It defaults to the first model returned from your account.",
)
@click.option(
    "--tournament",
    "-t",
    default=TOURNAMENTS["numerai"],
    help="Target a specific tournament number."
    " Defaults to Numerai Tournament/Classic."
    f" Available tournaments: {json.dumps(tournaments_dict(), indent=2)}",
)
@click.pass_context
def node(ctx, verbose, model_name, signals):
    """
    Commands to manage and test Prediction Nodes.
    """
    if not os.path.exists(CONFIG_PATH):
        click.secho(
            "cannot find .numerai config directory, " "run `numerai setup`", fg="red"
        )
        exit(1)

    logger = logging.getLogger("azure")
    if verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)

    models = get_models(signals)

    try:
        ctx.ensure_object(dict)
        ctx.obj["model"] = models[model_name]

    except KeyError:
        click.secho(
            f'Model with name "{model_name}" '
            f"found in list of models:\n{json.dumps(models, indent=2)}"
            f'\n(use the "-s" flag for signals models)',
            fg="red",
        )
        exit(1)


node.add_command(config)
node.add_command(deploy)
node.add_command(destroy)
node.add_command(test)
node.add_command(status)
