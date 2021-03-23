import json

import click
from numerapi import base_api

from numerai.cli.constants import *
from numerai.cli.node.config import config
from numerai.cli.node.deploy import deploy
from numerai.cli.node.destroy import destroy
from numerai.cli.node.test import test, status
from numerai.cli.util.keys import get_numerai_keys


@click.group()
@click.option(
    '--model-name', '-m', type=str, prompt=True,
    help=f"The name of one of your models to configure the Prediction Node for."
         f"It defaults to the first model returned from your account."
)
@click.option(
    '--signals', '-s', is_flag=True,
    help=f"Target a signals model with this name. Defaults to false."
)
@click.pass_context
def node(ctx, model_name, signals):
    """
    Commands to create, deploy, test, and destroy Prediction Nodes.
    """
    if not os.path.exists(CONFIG_PATH):
        click.secho('cannot find .numerai config directory, '
                    'run "numerai setup"', fg='red')
        exit(1)

    if signals:
        tournament = TOURNAMENT_SIGNALS
        name_prefix = 'signals'
    else:
        tournament = TOURNAMENT_NUMERAI
        name_prefix = 'numerai'
    napi = base_api.Api(*get_numerai_keys())
    models = napi.get_models(tournament)

    try:
        model_id = models[model_name]
        ctx.ensure_object(dict)
        ctx.obj['model'] = {
            'id': model_id,
            'name': f'{name_prefix}-{model_name}',
            'is_signals': signals
        }

    except KeyError:
        click.secho(
            f'No tournament {tournament} model with name "{model_name}" '
            f'found in list of models:\n{json.dumps(models, indent=2)}',
            fg='red'
        )
        return


node.add_command(config)
node.add_command(deploy)
node.add_command(destroy)
node.add_command(test)
node.add_command(status)
