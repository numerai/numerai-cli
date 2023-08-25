terraform {
  required_version = "1.5.6"
}

# Specify the provider and access details
provider "aws" {
  region = var.region
}

locals {
  nodes = jsondecode(file(var.node_config_file))
  aws_nodes = {
    for node, config in local.nodes :
    node => config if config.provider == "aws"
  }
}

module "aws" {
  count               = length(local.aws_nodes) > 0 ? 1 : 0
  source              = "./aws"
  aws_region          = var.region
  az_count            = var.az_count
  nodes               = local.aws_nodes
  node_container_port = var.node_container_port
  gateway_stage_path  = var.gateway_stage_path
}
