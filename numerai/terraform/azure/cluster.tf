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

# To be replaced by each node's repository name 
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

# Resource group for the submission node
resource "azurerm_resource_group" "rg" {
  location = var.az_rg_location
  name = "${local.node_prefix}-resource-grp"
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
      workspace_id = azurerm_log_analytics_workspace.function_app.workspace_id
      workspace_key = azurerm_log_analytics_workspace.function_app.primary_shared_key
    }
   }
    
  container {
    name   = "${var.container_name_prefix}-${random_string.random.result}"
    image  = var.image_url
    cpu    = var.cpu_cores
    memory = var.memory_in_gb

    ports {
      port     = var.node_container_port
      protocol = "TCP"
    }

  }
  
}