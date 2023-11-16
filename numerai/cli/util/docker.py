import sys
import base64
import subprocess
from queue import Queue, Empty
from threading import Thread

import boto3
import click

from numerai.cli.constants import *
from numerai.cli.util.debug import root_cause
from numerai.cli.util.keys import (
    sanitize_message,
    get_aws_keys,
    load_or_init_keys,
    get_azure_keys,
    get_gcp_keys,
    get_gcp_project,
)
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.containerregistry import ContainerRegistryClient, ArtifactManifestOrder
from azure.identity import ClientSecretCredential
import google.cloud.artifactregistry_v1 as artifactregistry_v1


def check_for_dockerfile(path):
    dockerfile_path = os.path.join(path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        click.secho(
            f"No Dockerfile found in {path}, please ensure this node "
            f"was created from an example or follows the Prediction Node Architecture. "
            f"Learn More:\nhttps://github.com/numerai/numerai-cli/wiki/Prediction-Nodes",
            fg="red",
        )
        exit(1)
    if Path.home() == dockerfile_path:
        click.secho(
            f"DO NOT PUT THE DOCKERFILE IN YOUR HOME PATH, please ensure this node "
            f"was created from an example or follows the Prediction Node Architecture. "
            f"Learn More:\nhttps://github.com/numerai/numerai-cli/wiki/Prediction-Nodes",
            fg="red",
        )
        exit(1)


def subprocess_log(stream, queue):
    for line in iter(stream.readline, b""):
        queue.put(line)
    stream.close()


def get_from_q(q, verbose, default=b"", prefix=""):
    try:
        res = q.get(block=False)
        if verbose and res:
            click.secho(f"{prefix} {res.decode()}")
        return res
    except Empty as e:
        return default


def execute(command, verbose, censor_substr=None):
    if verbose:
        click.echo("Running: " + sanitize_message(command, censor_substr))

    on_posix = "posix" in sys.builtin_module_names
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        close_fds=on_posix,
    )
    stdout_q = Queue()
    stderr_q = Queue()
    stdout_t = Thread(target=subprocess_log, args=(proc.stdout, stdout_q))
    stderr_t = Thread(target=subprocess_log, args=(proc.stderr, stderr_q))

    try:
        stdout_t.start()
        stderr_t.start()
        stdout = b""
        stderr = b""
        while proc.poll() is None:
            stdout += get_from_q(stdout_q, verbose)
            stderr += get_from_q(stderr_q, verbose)

        returncode = proc.poll()
        if returncode != 0:
            root_cause(stdout, stderr)
    finally:
        stdout_t.join()
        stderr_t.join()
        proc.kill()

    return stdout, stderr


def format_if_docker_toolbox(path, verbose):
    """
    Helper function to format if the system is running docker toolbox + mingw.
    Paths need to be formatted like unix paths, and the drive letter lower-cased
    """
    if "DOCKER_TOOLBOX_INSTALL_PATH" in os.environ and "MSYSTEM" in os.environ:
        # '//' found working on win8.1 docker quickstart terminal, previously just '/'
        new_path = ("//" + path[0].lower() + path[2:]).replace("\\", "/")
        if verbose:
            click.secho(f"formatted path for docker toolbox: {path} -> {new_path}")
        return new_path
    return path


# Added variable to take in different providers
def build_tf_cmd(tf_cmd, provider, env_vars, inputs, version, verbose):
    cmd = f"docker run"
    if env_vars:
        cmd += " ".join([f' -e "{key}={val}"' for key, val in env_vars.items()])
    cmd += f" --rm -it -v {format_if_docker_toolbox(CONFIG_PATH, verbose)}:/opt/plan"
    if provider == PROVIDER_GCP:
        cmd += (
            f" --mount type=bind,source={GCP_KEYS_PATH},target=/tmp/gcp_keys/keys.json"
        )
        cmd += f" -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_keys/keys.json"
        cmd += f" -e GOOGLE_PROJECT={get_gcp_project()}"
    cmd += f" -w /opt/plan hashicorp/terraform:{version}"
    # Added provider to pick the correct provider directory before tf command
    cmd += " ".join([f" -chdir={provider}"])
    cmd += f" {tf_cmd}"
    if inputs:
        cmd += " ".join([f' -var="{key}={val}"' for key, val in inputs.items()])
    return cmd


# Added variable to take in different providers
def terraform(tf_cmd, verbose, provider, env_vars=None, inputs=None, version="1.5.6"):
    cmd = build_tf_cmd(tf_cmd, provider, env_vars, inputs, version, verbose)
    stdout, stderr = execute(cmd, verbose)
    # if user accidentally deleted a resource, refresh terraform and try again
    if b"ResourceNotFoundException" in stdout or b"NoSuchEntity" in stdout:
        refresh = build_tf_cmd("refresh", env_vars, inputs, version, verbose)
        execute(refresh, verbose)
        stdout, stderr = execute(cmd, verbose)
    return stdout


def build(node_config, node, verbose):
    numerai_keys = load_or_init_keys()["numerai"]

    node_path = node_config["path"]
    curr_path = os.path.abspath(".")
    if curr_path not in node_path:
        raise RuntimeError(
            f"Current directory invalid, you must run this command either from"
            f' "{node_path}" or a parent directory of that path.'
        )
    path = node_path.replace(curr_path, ".").replace("\\", "/")
    if verbose:
        click.secho(f"Using relative path to node: {path}")

    build_arg_str = ""
    for arg in numerai_keys:
        build_arg_str += f" --build-arg {arg}={numerai_keys[arg]}"
    build_arg_str += f' --build-arg MODEL_ID={node_config["model_id"]}'
    build_arg_str += f" --build-arg SRC_PATH={path}"
    build_arg_str += f" --build-arg NODE={node}"

    cmd = (
        f'docker build --platform=linux/amd64 -t {node_config["docker_repo"]}' f"{build_arg_str} -f {path}/Dockerfile ."
    )
    execute(cmd, verbose)


def run(node_config, verbose, command=""):
    cmd = f"docker run --rm -it {node_config['docker_repo']} {command}"
    execute(cmd, verbose)


def login(node_config, verbose):
    if node_config["provider"] == PROVIDER_AWS:
        username, password = login_aws()
        login_url = node_config['docker_repo']
    elif node_config["provider"] == PROVIDER_AZURE:
        username, password = login_azure(node_config["registry_rg_name"], node_config["registry_name"])
        login_url = node_config['docker_repo']
    elif node_config["provider"] == PROVIDER_GCP:
        username, password = login_gcp()
        login_url = node_config['artifact_registry_login_url']
    else:
        raise ValueError(f"Unsupported provider: '{node_config['provider']}'")

    if os.name == "nt":
        echo_cmd = f'echo | set /p="{password}"'
    else:
        echo_cmd = f'echo "{password}"'

    cmd = (
        echo_cmd + f" | docker login"
        f" -u {username}"
        f" --password-stdin"
        f" {login_url}"
    )

    execute(cmd, verbose, censor_substr=password)


def login_aws():
    aws_public, aws_secret = get_aws_keys()
    ecr_client = boto3.client(
        "ecr",
        region_name="us-east-1",
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret,
    )

    token = ecr_client.get_authorization_token()  # TODO: use registryIds
    username, password = base64.b64decode(token["authorizationData"][0]["authorizationToken"]).decode().split(":")

    return username, password


def login_azure(resource_group_name, registry_name):
    azure_subs_id, azure_client, azure_tenant, azure_secret = get_azure_keys()
    credentials = ClientSecretCredential(client_id=azure_client, tenant_id=azure_tenant, client_secret=azure_secret)
    username_password = ContainerRegistryManagementClient(credentials, azure_subs_id).registries.list_credentials(
        resource_group_name, registry_name
    )
    username = username_password.username
    password = username_password.passwords[0].value
    return username, password


def login_gcp():
    gcp_keys_path = get_gcp_keys()
    gcp_keys_file = open(gcp_keys_path, "r")
    gcp_keys = gcp_keys_file.read()
    username = "_json_key_base64"
    password = base64.b64encode(gcp_keys.encode()).decode("utf-8")
    return username, password


def manifest_inspect(docker_image, verbose):
    cmd = f"docker manifest inspect {docker_image}"
    execute(cmd, verbose=verbose)


def push(docker_image, verbose):
    cmd = f"docker push {docker_image}"
    execute(cmd, verbose=verbose)


def pull(docker_image, verbose):
    cmd = f"docker pull {docker_image}"
    execute(cmd, verbose=verbose)


def tag(original_image, new_image_tag, verbose):
    cmd = f"docker tag {original_image} {new_image_tag}"
    execute(cmd, verbose=verbose)


def cleanup(node_config):
    provider = node_config["provider"]
    if provider == PROVIDER_AWS:
        imageIds = cleanup_aws(node_config["docker_repo"])
    elif provider == PROVIDER_AZURE:
        imageIds = cleanup_azure(node_config)
    elif provider == PROVIDER_GCP:
        imageIds = cleanup_gcp(node_config)
    else:
        raise ValueError(f"Unsupported provider: '{provider}'")

    if len(imageIds) > 0:
        click.secho(
            f"Deleted {str(len(imageIds))} old image(s) from remote docker repo",
            fg="yellow",
        )


def cleanup_aws(docker_repo):
    aws_public, aws_secret = get_aws_keys()
    ecr_client = boto3.client(
        "ecr",
        region_name="us-east-1",
        aws_access_key_id=aws_public,
        aws_secret_access_key=aws_secret,
    )

    docker_repo_name = docker_repo.split("/")[-1]

    resp = ecr_client.list_images(repositoryName=docker_repo_name, filter={"tagStatus": "UNTAGGED"})

    imageIds = resp["imageIds"]
    if len(imageIds) == 0:
        return []

    resp = ecr_client.batch_delete_image(repositoryName=docker_repo_name, imageIds=imageIds)

    return resp["imageIds"]


def cleanup_azure(node_config):
    _, azure_client, azure_tenant, azure_secret = get_azure_keys()
    credentials = ClientSecretCredential(client_id=azure_client, tenant_id=azure_tenant, client_secret=azure_secret)
    acr_client = ContainerRegistryClient(node_config["acr_login_server"], credentials)
    docker_repo = node_config["docker_repo"]
    node_repo_name = [
        repo_name for repo_name in acr_client.list_repository_names() if repo_name == docker_repo.split("/")[-1]
    ][0]

    # get all manifests, ordered by last update time
    manifest_list = [
        repo_detail
        for repo_detail in acr_client.list_manifest_properties(
            node_repo_name, order_by=ArtifactManifestOrder.LAST_UPDATED_ON_DESCENDING
        )
    ]
    # Remove all but the latest manifest
    removed_manifests = []
    for manifest in manifest_list[1:]:
        acr_client.update_manifest_properties(node_repo_name, manifest.digest, can_write=True, can_delete=True)
        removed_manifests.append(manifest.digest)
        acr_client.delete_manifest(node_repo_name, manifest.digest)
    return removed_manifests


def cleanup_gcp(node_config):
    print(node_config)
    gcp_key_path = get_gcp_keys()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_key_path

    node_name = node_config["docker_repo"].split("/")[-1]

    client = artifactregistry_v1.ArtifactRegistryClient()
    list_images_request = artifactregistry_v1.ListDockerImagesRequest(
        parent=node_config["registry_id"]
    )
    page_result = client.list_docker_images(request=list_images_request)

    latest_image_name = ""
    for response in page_result:
        if "latest" in response.tags:
            latest_image_name = response.name

    versions = artifactregistry_v1.ListVersionsRequest(
        parent=f"{node_config['registry_id']}/packages/{node_name}"
    )
    page_result = client.list_versions(request=versions)
    versions_to_delete = []
    for response in page_result:
        if response.metadata["name"] != latest_image_name:
            versions_to_delete.append(response.name)

    for version in versions_to_delete:
        result = client.delete_version(name=version)

    # Nothing to do
    return versions_to_delete
