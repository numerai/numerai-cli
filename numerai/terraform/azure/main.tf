# https://learn.microsoft.com/en-us/azure/developer/terraform/create-resource-group?tabs=azure-cli

terraform {
  required_version = ">= 0.12"  #">=0.12"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.57"
    }
  }
}

provider "azurerm" {
    #subscription_id = "your sub id"  
    #client_id       = "your client id"  
    #client_secret   = "your client secret"  
    #tenant_id       = "your tenant id"  
  features {}

  # tells Terraform to use a managed identity 
  # use_msi = true
}

#resource "random_pet" "rg_name" {
  #prefix = var.az_resource_group_prefix
  #prefix = locals.node_prefix
#  description = "Generate random pet name to be appended as resource group name"
#}

#"Resource group for the submission node"
resource "azurerm_resource_group" "rg" {
  location = var.az_resource_group_location
  name = "${local.node_prefix}-resource-grp"
  #name     = random_pet.rg_name.id
  #prefix = locals.node_prefix
}

# eses: Followings are referencing aws version, disabling for now
# Read the node configuration file to get node details
#locals {
#  nodes = jsondecode(file(var.node_config_file))
#  azure_nodes = {
#    for node, config in local.nodes:
#    node => config if config.provider == "azure"
#  }
#}

