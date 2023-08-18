# Resource group for the submission node
resource "azurerm_resource_group" "rg" {
  for_each = { for name, config in var.nodes : name => config }
  location = var.az_resource_group_location
  name     = "${each.key}-resource-grp"
}

# Container Instance
variable "restart_policy" {
  type        = string
  description = "The behavior of Azure runtime if container has stopped."
  default     = "Never"
  validation {
    condition     = contains(["Always", "Never", "OnFailure"], var.restart_policy)
    error_message = "The restart_policy must be one of the following: Always, Never, OnFailure."
  }
}

resource "azurerm_log_analytics_workspace" "container_instance" {
  for_each            = { for name, config in var.nodes : name => config }
  name                = "${local.node_prefix}-aci-log-analytics-${random_string.random[each.key].result}"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}


data "azurerm_resource_group" "acr_rg" {
  name = "numerai-cli-acr-resource-grp"
}

data "azurerm_container_registry" "registry" {
  name                = input.registry_name
  resource_group_name = data.azurerm_resource_group.acr_rg.name
}

# Create a container group with single container
resource "azurerm_container_group" "container" {
  for_each            = { for name, config in var.nodes : name => config }
  name                = "${local.node_prefix}-container-group-${random_string.random[each.key].result}"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  ip_address_type     = "Public"
  os_type             = "Linux"
  restart_policy      = var.restart_policy

  diagnostics {
    log_analytics {
      log_type      = "ContainerInsights"
      workspace_id  = azurerm_log_analytics_workspace.container_instance[each.key].workspace_id
      workspace_key = azurerm_log_analytics_workspace.container_instance[each.key].primary_shared_key
    }
  }

  image_registry_credential {
    username = data.azurerm_container_registry.registry.admin_username
    password = data.azurerm_container_registry.registry.admin_password
    server   = data.azurerm_container_registry.registry.login_server
  }

  container {
    name   = "submission-node-${random_string.random[each.key].result}"
    image  = each.value.docker_repo
    cpu    = each.value.cpu / 1024
    memory = each.value.memory / 1024

    ports {
      port     = var.node_container_port
      protocol = "TCP"
    }
  }
}
