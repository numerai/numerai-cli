terraform {
  #required_version = "~> 0.14.0"
  required_version = ">= 0.12" # for Azure compatibility

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.57"
    }
  }
}

# ISSUE: need to have multiple provider keys! else will have error during "numerai node config"
# Provider not recommended to be defined within a module -> else cannot use count/for_each on module block
# https://developer.hashicorp.com/terraform/language/modules/develop/providers
# Specify the provider and access details
#provider "aws" {
#  region  = var.region
#}

# Added for Azure compatibility
provider "azurerm" {
  #subscription_id = #"ARM_SUBSCRIPTION_ID"
  #client_id       = #"ARM_CLIENT_ID"
  #tenant_id       = #"ARM_TENANT_ID"
  #61client_secret   = #"ARM_CLIENT_SECRET"

  features {}
  # tells Terraform to use a managed identity 
  #use_msi = true
}

# Parse the node_config_file and create dictionaries of nodes, by providers
locals {
  nodes = jsondecode(file(var.node_config_file))
  aws_nodes = {
    for node, config in local.nodes:
    node => config if config.provider == "aws"
  }

  # eses: parse the node_config_file and create a dictionary of azure nodes
  azure_nodes = {
    for node, config in local.nodes:
    node => config if config.provider == "azure"
  }
}

#module "aws" {
#  count = length(local.aws_nodes) > 0 ? 1 : 0
#  source = "./aws"
#  aws_region = var.region
#  az_count = var.az_count
#  nodes = local.aws_nodes
# node_container_port = var.node_container_port
#  gateway_stage_path = var.gateway_stage_path
#}

# WIP: to link with Azure module's input.tf variables
module "azure" {
  count = length(local.azure_nodes) > 0 ? 1 : 0
  source = "./azure"
  az_rg_location = var.az_rg_location
  nodes = local.azure_nodes
  node_container_port = var.node_container_port
  # Add other variables required by Azure module's input.tf
}