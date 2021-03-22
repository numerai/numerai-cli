import os

import click

from numerai.cli.util import files, docker


@click.command()
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def deploy(ctx, verbose):
    """Builds and pushes your docker image to the AWS ECR repo"""
    ctx.ensure_object(dict)
    model = ctx.obj['model']
    node = model['name']
    node_config = files.load_or_init_nodes(node)

    docker.check_for_dockerfile(node_config['path'])

    click.echo('building container image...')
    docker.build(node_config, verbose)

    click.echo('logging into container registry...')
    docker.login(node_config, verbose)

    click.echo('pushing image to registry...')
    docker.push(node_config['docker_repo'])

    click.echo('cleaning up local images...')
    docker.cleanup(node_config)
