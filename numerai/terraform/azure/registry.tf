resource "random_string" "registry_name_random" {
  count   = length(local.azure_nodes) > 0 ? 1 : 0
  length  = 10
  lower   = true
  upper   = false
  special = false
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
  count               = length(local.azure_nodes) > 0 ? 1 : 0
  name                = "NumeraiACR${random_string.registry_name_random[0].result}"
  resource_group_name = azurerm_resource_group.acr_rg[0].name
  location            = azurerm_resource_group.acr_rg[0].location
  sku                 = var.registry_sku
  admin_enabled       = true
}

output "acr_repo_details" {
  value = length(local.azure_nodes) > 0 ? {
    registry_rg_name = azurerm_resource_group.acr_rg[0].name
    registry_name    = azurerm_container_registry.registry[0].name
    acr_login_server = azurerm_container_registry.registry[0].login_server
  } : null
}
