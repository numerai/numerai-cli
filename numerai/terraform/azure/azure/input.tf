# Store all terraform variables in this file
variable "az_resource_group_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}

variable "nodes" {
  description = "Map of node names to their configurations"
  type        = map(map(any))
}

variable "node_container_port" {
  description = "Port exposed by the container instance to redirect traffic to"
  type        = number
  default     = 3000
}

variable "registry_name" {
  description = "Name of Azure container registry"
  type = string
}