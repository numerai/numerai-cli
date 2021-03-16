import numerapi

from cli.src.constants import *
from cli.src.util.files import \
    format_path_if_mingw,\
    load_or_init_nodes,\
    store_config
from cli.src.util.docker import terraform
from cli.src.util.keys import get_provider_keys, get_numerai_keys


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
        nodes_config = load_or_init_nodes()
        node_config = nodes_config[node]
        provider_keys = get_provider_keys(node)
    except (KeyError, FileNotFoundError) as e:
        click.secho(f"make sure you run `numerai setup` and "
                    f"`numerai node -n {node} create` first...", fg='red')
        return

    try:
        click.secho(f"deleting node configuration...")
        del nodes_config[node]
        store_config(NODES_PATH, nodes_config)

        click.secho(f"deleting cloud resources for node...")
        terraform(f'apply -auto-approve -var="node_config_file=nodes.json"', verbose,
                  env_vars=provider_keys)

    except Exception as e:
        click.secho(e.__str__(), fg='red')
        nodes_config[node] = node_config
        store_config(NODES_PATH, nodes_config)
        return

    if 'model_id' in node_config:
        napi = numerapi.NumerAPI(*get_numerai_keys())
        model_id = node_config['model_id']
        webhook_url = node_config['webhook_url']
        click.echo(f'deregistering webhook {webhook_url} for model {model_id}...')
        napi.raw_query(
            '''
            mutation (
                $modelId: String!
                $newSubmissionWebhook: String!
            ) {
                setSubmissionWebhook(
                    modelId: $modelId
                    newSubmissionWebhook: $newSubmissionWebhook
                )
            }
            ''',
            variables={
                'modelId': model_id,
                'newSubmissionWebhook': None
            },
            authorization=True
        )
