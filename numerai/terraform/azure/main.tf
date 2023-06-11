# https://learn.microsoft.com/en-us/azure/developer/terraform/create-resource-group?tabs=azure-cli
terraform {
  required_version = ">= 0.12"  #">=0.12"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.57"
    }
  # https://stackoverflow.com/questions/68580196/how-to-push-a-docker-image-to-azure-container-registry-using-terraform
    #docker = {
    #  source  = "kreuzwerker/docker"
    #  version = ">= 2.16.0"
    #}
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


#provider "docker" {
#  #host = "tcp://localhost:2376"

#  registry_auth {
#   address  = azurerm_container_registry.registry.login_server
#    username = azurerm_container_registry.registry.admin_username
#    password = azurerm_container_registry.registry.admin_password
#  }

  #depends on is being reserved, so must use -target="azurerm_container_registry.registry" to create the registry first
  #depends_on = [azurerm_container_registry.registry]
#}


# eses: Followings are referencing aws version, disabling for now
# Read the node configuration file to get node details
#locals {
#  nodes = jsondecode(file(var.node_config_file))
#  azure_nodes = {
#    for node, config in local.nodes:
#    node => config if config.provider == "azure"
#  }
#}

