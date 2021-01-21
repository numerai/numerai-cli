terraform {
  required_version = "~> 0.14.0"
}

# Specify the provider and access details
provider "aws" {
  profile = "default"
  region  = var.region
}

locals {
  apps = jsondecode(file(var.app_config_file))
  aws_apps = [for app, config in local.apps:
    merge({name: app}, config) if config.provider == "aws"
  ]
}

module "aws" {
  count = length(local.aws_apps) > 0 ? 1 : 0
  source = "./aws"
  aws_region = var.region
  az_count = var.az_count
  applications = local.aws_apps
  app_port = var.app_port
  gateway_stage_path = var.gateway_stage_path
}