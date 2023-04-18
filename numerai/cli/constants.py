import os
import json
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
LOG_TYPES = [LOG_TYPE_WEBHOOK, LOG_TYPE_CLUSTER]

SIZE_PRESETS = {
    # balanced cpu/mem
    "gen-xs": (512, 1908),
    "gen-sm": (1024, 3816),
    "gen-md": (2048, 7630),
    "gen-lg": (4096, 15260),
    "gen-xl": (8192, 30520),
    "gen-2xl": (16384, 61035),
    # cpu heavy
    "cpu-xs": (512, 954),
    "cpu-sm": (1024, 1908),
    "cpu-md": (2048, 3816),
    "cpu-lg": (4096, 7630),
    "cpu-xl": (8192, 15260),
    "cpu-2xl": (16384, 30520),
    # mem heavy
    "mem-xs": (512, 3816),
    "mem-sm": (1024, 7630),
    "mem-md": (2048, 15260),
    "mem-lg": (4096, 30520),
    "mem-xl": (8192, 61035),
    "mem-2xl": (16384, 114441),
}

DEFAULT_EXAMPLE = 'tournament-python3'
DEFAULT_SIZE = "mem-md"
DEFAULT_PROVIDER = PROVIDER_AWS
DEFAULT_PATH = os.getcwd()
DEFAULT_SETTINGS = {
    'provider': DEFAULT_PROVIDER,
    'cpu': SIZE_PRESETS[DEFAULT_SIZE][0],
    'memory': SIZE_PRESETS[DEFAULT_SIZE][1],
    'path': DEFAULT_PATH,
}

CONSTANTS_STR = f'''Default values (not your configured node values):

---Tournament Numbers---
TOURNAMENT_NUMERAI: {TOURNAMENT_NUMERAI}
TOURNAMENT_SIGNALS: {TOURNAMENT_SIGNALS}

---Paths---
PACKAGE_PATH: {PACKAGE_PATH}
CONFIG_PATH: {CONFIG_PATH}
KEYS_PATH: {KEYS_PATH}
NODES_PATH: {NODES_PATH}
TERRAFORM_PATH: {TERRAFORM_PATH}
EXAMPLE_PATH: {EXAMPLE_PATH}

---Cloud Interaction---
PROVIDERS: {PROVIDERS}
LOG_TYPES: {LOG_TYPES}

---Prediction Nodes---
DEFAULT_EXAMPLE: {DEFAULT_EXAMPLE}
DEFAULT_SIZE: {DEFAULT_SIZE}
DEFAULT_PROVIDER: {DEFAULT_PROVIDER}
DEFAULT_PATH: {DEFAULT_PATH}
DEFAULT_SETTINGS: {json.dumps(DEFAULT_SETTINGS, indent=2)}
'''
