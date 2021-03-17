import json

import numerapi

from cli.src.constants import *
from cli.src.util.keys import get_numerai_keys
from cli.src.node.create import create
from cli.src.node.deploy import deploy
from cli.src.node.destroy import destroy
from cli.src.node.test import LOG_TYPES, test, status


@click.group()
@click.option(
    '--model-name', '-m', type=str,
    help=f"The name of one of your models to configure the Prediction Node for."
         f"It defaults to the first model returned from your account."
)
@click.pass_context
def node(ctx, model_name):
    """
    Commands to create, deploy, test, and destroy Prediction Nodes.
    """
    if not os.path.exists(CONFIG_PATH):
        click.secho('cannot find .numerai config directory, '
                    'run "numerai setup"', fg='red')
        exit(1)

    napi = numerapi.NumerAPI(*get_numerai_keys())
    acct = napi.get_account()
    models = acct['models']
    latest_model = models[0]
    if model_name is None and not click.confirm(
        f"Use default model '{latest_model['name']}'?"
    ):
        model_name = click.prompt(
            'Provide one of your model name '
            '(or use the --model-name option as a shortcut):'
        )
    try:
        model = list(filter(
            lambda m: model_name is None or m['name'] == model_name,
            models
        ))[0]
        ctx.ensure_object(dict)
        ctx.obj['model'] = {'id': model['id'], 'name': model['name']}
    except IndexError:
        click.secho(f'No model with name {model_name} found in list of models:\n'
                    f'{json.dumps(list(map(lambda m: m["name"], models)), indent=2)}',
                    fg='red')


node.add_command(create)
node.add_command(deploy)
node.add_command(destroy)
node.add_command(test)
node.add_command(status)
