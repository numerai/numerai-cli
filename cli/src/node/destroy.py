from cli.src.constants import *
from cli.src.util.files import \
    format_path_if_mingw,\
    load_or_init_nodes,\
    store_config
from cli.src.util.docker import terraform
from cli.src.util.keys import get_provider_keys


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def destroy(ctx, verbose):
    """
    Uses Terraform to destroy Numerai Compute cluster in AWS.
    This will delete everything, including:
        - lambda url
        - docker container and associated task
        - all logs
    This command is idempotent and safe to run multiple times.
    """
    ctx.ensure_object(dict)
    node = ctx.obj['node']
    if not os.path.exists(CONFIG_PATH):
        click.secho(f".numerai directory not setup, "
                    f"run 'numerai setup'...",
                    fg='red')
        return
    numerai_dir = format_path_if_mingw(CONFIG_PATH)

    try:
        click.secho(f"deleting node configuration...")
        nodes_config = load_or_init_nodes()
        del nodes_config[node]
        store_config(NODES_PATH, nodes_config)

        click.secho(f"deleting cloud resources for node...")
        terraform(f'apply -auto-approve -var="node_config_file=nodes.json"',
                  numerai_dir, verbose, env_vars=get_provider_keys(node))

    except (KeyError, FileNotFoundError):
        click.secho(f"run `numerai node -n {node} create` first...", fg='red')
        return
