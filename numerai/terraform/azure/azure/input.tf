# Store all terraform variables in this file
variable "az_rg_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}

# Put into locals
#variable "az_resource_group_prefix" {
#  default     = "numerai"
#  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
#}

# Referecing aws version, to load the node names and their configurations
variable "nodes" {
  description = "Map of node names to their configurations"
  type        = map(map(any))
}

variable "node_container_port" {
  description = "Port exposed by the container instance to redirect traffic to"
  type        = number
  default     = 3000
}

