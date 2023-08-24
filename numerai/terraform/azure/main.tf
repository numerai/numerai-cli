terraform {
  required_version = ">= 0.12"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.57"
    }
  }
}

# Auth passed via .numerai/.keys already
provider "azurerm" {
  skip_provider_registration = true
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Read the node configuration file to get node details
locals {
  nodes = jsondecode(file(var.node_config_file))
  azure_nodes = {
    for node, config in local.nodes :
    node => config if config.provider == "azure"
  }
}

resource "azurerm_resource_group" "acr_rg" {
  count    = length(local.azure_nodes) > 0 ? 1 : 0
  location = var.az_resource_group_location
  name     = "numerai-cli-acr-resource-grp"
}

module "azure" {
  count                      = length(local.azure_nodes) > 0 ? 1 : 0
  source                     = "./azure"
  az_resource_group_location = var.az_resource_group_location
  nodes                      = local.azure_nodes
  node_container_port        = var.node_container_port
  registry_name              = azurerm_container_registry.registry[0].name

  depends_on = [
    azurerm_container_registry.registry[0],
    azurerm_resource_group.acr_rg
  ]
}

