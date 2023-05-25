# https://learn.microsoft.com/en-us/azure/developer/terraform/create-resource-group?tabs=azure-cli

terraform {
  required_version = ">= 0.12"  #">=0.12"

  #required_providers {
  #  azurerm = {
  #    source  = "hashicorp/azurerm"
  #    version = "~>2.0"
  #  }
  #  random = {
  #    source  = "hashicorp/random"
  #    version = "~>3.0"
  #  }
  #}
}

provider "azurerm" {
  features {}
}

#resource "random_pet" "rg_name" {
  #prefix = var.az_resource_group_prefix
  #prefix = locals.node_prefix
#  description = "Generate random pet name to be appended as resource group name"
#}

resource "azurerm_resource_group" "rg" {
  location = var.az_resource_group_region
  #name     = random_pet.rg_name.id
  #prefix = locals.node_prefix
  name= "${local.node_prefix}-resource-grp"
}

# eses: Followings are referencing aws version, disabling for now
#locals {
#  nodes = jsondecode(file(var.node_config_file))
#  azure_nodes = {
#    for node, config in local.nodes:
#    node => config if config.provider == "azure"
#  }
#}

