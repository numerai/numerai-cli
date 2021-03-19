import os
from pathlib import Path


TOURNAMENT_NUMERAI = 8
TOURNAMENT_SIGNALS = 11
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

LOG_TYPE_WEBHOOK = 'webhook'
LOG_TYPE_CLUSTER = 'cluster'
LOG_TYPES = [
    LOG_TYPE_WEBHOOK,
    LOG_TYPE_CLUSTER
]

SIZE_PRESETS = {
    "gen-sm": (1024, 4096),
    "gen-md": (2048, 8192),
    "gen-lg": (4096, 16384),

    "cpu-sm": (1024, 2048),
    "cpu-md": (2048, 4096),
    "cpu-lg": (4096, 8192),

    "mem-sm": (1024, 8192),
    "mem-md": (2048, 16384),
    "mem-lg": (4096, 30720),
}

DEFAULT_EXAMPLE = 'tournament-python3'
DEFAULT_SIZE = "gen-md"
DEFAULT_PROVIDER = PROVIDER_AWS
DEFAULT_PATH = os.getcwd()
DEFAULT_SETTINGS = {
    'provider': DEFAULT_PROVIDER,
    'cpu': SIZE_PRESETS[DEFAULT_SIZE][0],
    'memory': SIZE_PRESETS[DEFAULT_SIZE][1],
    'path': DEFAULT_PATH
}
