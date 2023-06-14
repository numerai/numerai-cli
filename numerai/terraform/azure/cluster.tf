# Resource group for the submission node
resource "azurerm_resource_group" "rg" {
  location = var.az_resource_group_location
  name = "${var.node_name}-resource-grp"
  #name = "${local.node_prefix}-resource-grp"
  #prefix = locals.node_prefix
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

# To be replaced by each node's repository name 
#variable "image_url" {
#  type        = string
#  description = "Container image to deploy. Should be of the form repoName/imagename:tag for images stored in public Docker Hub, or a fully qualified URL for other registries. Images from private registries require additional registry credentials."
#  default     = "docker.io/eseswaiga/test-new:latest"
#}

resource "random_string" "random" {
  length  = 10
  lower = true
  upper = false
  special = false
}

#variable "registry_sku" {
#  type        = string
#  description = "The sku option of Azure Container Registry"
#  default     = "Basic"
# validation {
#    condition     = contains(["Basic", "Standard", "Premium"], var.registry_sku)
#    error_message = "The registry_sku must be one of the following: Basic, Standard, Premium."
#  }
#}

# Add support for container registry
# Does not support non alphanumeric characters in the name
#resource "azurerm_container_registry" "registry" {
#  name                = "NumeraiACR${random_string.random.result}"
#  resource_group_name = azurerm_resource_group.rg.name
#  location            = azurerm_resource_group.rg.location
#  sku                 = var.registry_sku
#  admin_enabled       = true
#}

resource "azurerm_log_analytics_workspace" "container_instance" {
  name                = "container-instance-log-analytics"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}


data "azurerm_resource_group" "acr_rg" {
  name                = "numerai-cli-acr-resource-grp"
}

data "azurerm_container_registry" "registry" {
  name                = local.node_config[var.node_name].registry_name
  resource_group_name = data.azurerm_resource_group.acr_rg.name
}

# Create a container group with single container
## TODO: interate container instance creation for_each nodes in var.nodes
resource "azurerm_container_group" "container" {
  #for_each = { for name, config in var.nodes : name => config }
  name                = "${local.node_prefix}-azure-container-group"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  ip_address_type     = "Public"
  os_type             = "Linux"
  restart_policy      = var.restart_policy

  diagnostics {
    log_analytics {
      log_type = "ContainerInsights"
      workspace_id = azurerm_log_analytics_workspace.container_instance.workspace_id
      workspace_key = azurerm_log_analytics_workspace.container_instance.primary_shared_key
    }
  }

  image_registry_credential {
    username = data.azurerm_container_registry.registry.admin_username
    password = data.azurerm_container_registry.registry.admin_password
    server = data.azurerm_container_registry.registry.login_server
    #user_assigned_identity_id = azurerm_user_assigned_identity.containerapp[each.key].id
  }
    
  container {
    #name   = "${var.container_name_prefix}-${random_string.random.result}"
    #image  = "${azurerm_container_registry.registry.login_server}/${var.node_name}"
    #image  = var.image_url
    #cpu    = var.cpu_cores
    #memory = var.memory_in_gb
    name   = "submission-node"
    image  = local.node_config[var.node_name].docker_repo
    cpu    = local.node_config[var.node_name].cpu/1024
    memory = local.node_config[var.node_name].memory/1024

    ports {
      port     = var.node_container_port
      protocol = "TCP"
    }

  }

  depends_on = [
    #azurerm_container_registry.registry,
    azurerm_log_analytics_workspace.container_instance
  ]

  
}