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

# Load from the nodes.json file
#variable "node_config_file" {
#  description = "Path to the json file used to configure nodes"
#  type        = string
#  default     = "nodes.json" #TODO: remove after all tests complete
#}

#variable "node_name" {
#  description = "Name used to identify the node"
#  type        = string
#  default     = "" 
#}

# Identify the current node's node_config from the nodes.json file
#locals {
#  nodes = jsondecode(file(var.node_config_file))
#
#  node_config = {
#    for node, config in local.nodes:
#    node => config if config.provider == "azure" && node == var.node_name
#  }
#}
