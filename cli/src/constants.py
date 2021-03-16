import os
from pathlib import Path
import click

PACKAGE_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(str(Path.home()), '.numerai')
KEYS_PATH = os.path.join(CONFIG_PATH, '.keys')
NODES_PATH = os.path.join(CONFIG_PATH, 'nodes.json')
TERRAFORM_PATH = os.path.join(PACKAGE_PATH, "..", "terraform")
EXAMPLE_PATH = os.path.join(PACKAGE_PATH, "..", "examples")

EXAMPLES = os.listdir(EXAMPLE_PATH)

PROVIDER_AWS = "aws"
# PROVIDER_GCP = "gcp"
PROVIDERS = [
    PROVIDER_AWS,
    # PROVIDER_GCP
]

SIZE_PRESETS = {
    "gen-sm": (1024, 4096),
    "gen-md": (2048, 8192),
    "gen-lg": (4096, 16384),
    "gen-xl": (8192, 30720),

    "cpu-sm": (1024, 2048),
    "cpu-md": (2048, 4096),
    "cpu-lg": (4096, 8192),
    "cpu-xl": (8192, 16384),

    "mem-sm": (1024, 8192),
    "mem-md": (2048, 16384),
    "mem-lg": (4096, 30720),
}

DEFAULT_EXAMPLE = 'tournament-python3'
DEFAULT_NODE = "default"
DEFAULT_SIZE = "gen-md"
DEFAULT_PROVIDER = PROVIDER_AWS
DEFAULT_PATH = os.getcwd()
DEFAULT_SETTINGS = {
    'provider': DEFAULT_PROVIDER,
    'cpu': SIZE_PRESETS[DEFAULT_SIZE][0],
    'memory': SIZE_PRESETS[DEFAULT_SIZE][1],
    'path': DEFAULT_PATH
}


@click.command()
def size_presets():
    for size, preset in SIZE_PRESETS.items():
        suffix = '(default)' if size == DEFAULT_SIZE else ''
        color = 'green' if size == DEFAULT_SIZE else 'yellow'
        click.secho(
            f'{size} -> cpus: {preset[0] / 1024}, mem: {preset[1]/1024} GB {suffix}',
            fg=color
        )
    click.secho("See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html for more info")
