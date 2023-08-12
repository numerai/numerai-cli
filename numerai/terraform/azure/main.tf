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
    #subscription_id = "your sub id"  
    #client_id       = "your client id"  
    #client_secret   = "your client secret"  
    #tenant_id       = "your tenant id"  
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  # tells Terraform to use a managed identity 
  # use_msi = true
}

# Read the node configuration file to get node details
locals {
  nodes = jsondecode(file(var.node_config_file))
  azure_nodes = {
    for node, config in local.nodes:
    node => config if config.provider == "azure"
  }
}

module "azure" {
  count = length(local.azure_nodes) > 0 ? 1 : 0
  source = "./azure"
  az_resource_group_location = var.az_resource_group_location
  nodes = local.azure_nodes
  node_container_port = var.node_container_port
}