terraform {
  required_version = "~> 0.14.0"
}

# Specify the provider and access details
provider "aws" {
  region  = var.region
}

locals {
  nodes = jsondecode(file(var.node_config_file))
  aws_nodes = {
    for node, config in local.nodes:
    node => config if config.provider == "aws"
  }

  # eses: added temporarily to test azure
  azure_nodes = {
    for node, config in local.nodes:
    node => config if config.provider == "azure"
  }
}

module "aws" {
  count = length(local.aws_nodes) > 0 ? 1 : 0
  source = "./aws"
  aws_region = var.region
  az_count = var.az_count
  nodes = local.aws_nodes
  node_container_port = var.node_container_port
  gateway_stage_path = var.gateway_stage_path
}

# eses: added temporarily to test azure
module "azure" {
  count = length(local.azure_nodes) > 0 ? 1 : 0
  source = "./azure"
  azure_location = var.az_resource_group_location
  #az_count = var.az_count
  nodes = local.azure_nodes
  node_container_port = var.node_container_port # Keep for now, 3000
  #gateway_stage_path = var.gateway_stage_path
}
