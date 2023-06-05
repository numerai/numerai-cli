# Container Instance

# Resource group for the submission node
resource "azurerm_resource_group" "rg" {
  for_each = { for name, config in var.nodes : name => config }
  name     = "${each.key}-resource-grp"
  location = var.az_rg_location
}

variable "restart_policy" {
  type        = string
  description = "The behavior of Azure runtime if container has stopped."
  default     = "Never"
  validation {
    condition     = contains(["Always", "Never", "OnFailure"], var.restart_policy)
    error_message = "The restart_policy must be one of the following: Always, Never, OnFailure."
  }
}

variable "container_group_name_prefix" {
  type        = string
  description = "Prefix of the container group name that's combined with a random value so name is unique in your Azure subscription."
  default     = "acigroup"
}

# Temporary, to be replaced by each node's name
variable "container_name_prefix" {
  type        = string
  description = "Prefix of the container name that's combined with a random value so name is unique in your Azure subscription."
  default     = "aci"
}

# To be replaced by each node's repository URL 
variable "image_url" {
  type        = string
  description = "Container image to deploy. Should be of the form repoName/imagename:tag for images stored in public Docker Hub, or a fully qualified URL for other registries. Images from private registries require additional registry credentials."
  default     = "docker.io/eseswaiga/test-new:latest"
}

variable "cpu_cores" {
  type        = number
  description = "The number of CPU cores to allocate to the container."
  default     = 1
}

variable "memory_in_gb" {
  type        = number
  description = "The amount of memory to allocate to the container in gigabytes."
  default     = 2
}

resource "random_string" "random" {
  length  = 5
  lower = true
  upper = false
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

# Add support for container registry
# Does not support non alphanumeric characters in the name
resource "azurerm_container_registry" "registry" {
  for_each = { for name, config in var.nodes : name => config }
  name                = "NumeraiSubmissionContainerRegistry"
  resource_group_name = azurerm_resource_group.rg[each.key].name
  location            = azurerm_resource_group.rg[each.key].location
  sku                 = var.registry_sku
  admin_enabled       = true
}

resource "azurerm_log_analytics_workspace" "container_instance" {
  for_each     = { for name, config in var.nodes : name => config }
  name                = "container-instance-log-analytics"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Create a container group with single container
# name rules: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules#microsoftcontainerinstance
resource "azurerm_container_group" "container" {
  for_each = { for name, config in var.nodes : name => config }
  name                = "${local.node_prefix}-container-${random_string.random.result}"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  ip_address_type     = "Public"
  os_type             = "Linux"
  restart_policy      = var.restart_policy

   diagnostics {
    log_analytics {
      log_type = "ContainerInsights"
      workspace_id = azurerm_log_analytics_workspace.container_instance[each.key].workspace_id
      workspace_key = azurerm_log_analytics_workspace.container_instance[each.key].primary_shared_key
    }
   }
    
  container {
    #name   = "${var.container_name_prefix}-submission-node" #random_string.random.result
    name   = "submission-node"
    #image  = var.image_url #TODO: add support for container registry's URL and credentials
    image  = "${azurerm_container_registry.registry[each.key].login_server}/${each.key}" #TODO: add support for container registry's URL and credentials
    cpu    = each.value.cpu/1024#var.cpu_cores
    memory = each.value.memory/1024#var.memory_in_gb

    ports {
      port     = var.node_container_port
      protocol = "TCP"
    }
  }

  image_registry_credential {
    username = azurerm_container_registry.registry[each.key].admin_username
    password = azurerm_container_registry.registry[each.key].admin_password
    server = azurerm_container_registry.registry[each.key].login_server
  }


}