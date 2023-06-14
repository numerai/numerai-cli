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
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

resource "random_string" "random" {
  length  = 10
  lower = true
  upper = false
  special = false
}

variable "az_resource_group_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}

resource "azurerm_resource_group" "acr_rg" {
  location = var.az_resource_group_location
  name = "numerai-cli-acr-resource-grp"
}

variable "registry_sku" {
  type        = string
  description = "The sku option of Azure Container Registry"
  default     = "Basic"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.registry_sku)
    error_message = "The registry_sku must be one of the following: Basic, Standard, Premium."
  }
}

# Does not support non alphanumeric characters in the name
resource "azurerm_container_registry" "registry" {
  name                = "NumeraiACR${random_string.random.result}"
  resource_group_name = azurerm_resource_group.acr_rg.name
  location            = azurerm_resource_group.acr_rg.location
  sku                 = var.registry_sku
  admin_enabled       = true
}