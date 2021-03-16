from cli.src.constants import *

from cli.src.node.create import create, copy_example
from cli.src.node.deploy import deploy
from cli.src.node.destroy import destroy
from cli.src.node.test import LOG_TYPES, test, status


@click.group()
@click.option(
    '--name', '-n', type=str, default=DEFAULT_NODE,
    help=f"Target a node. Defaults to {DEFAULT_NODE}."
)
@click.pass_context
def node(ctx, name):
    """
    Commands to create, deploy, test, and destroy Prediction Nodes.
    """
    ctx.ensure_object(dict)
    ctx.obj['node'] = name

    if not os.path.exists(CONFIG_PATH):
        click.secho(
            'cannot find .numerai config directory, run "numerai setup"', fg='red'
        )
        exit(1)


node.add_command(create)
node.add_command(copy_example)
node.add_command(deploy)
node.add_command(destroy)
node.add_command(test)
node.add_command(status)
