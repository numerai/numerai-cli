# Store all terraform variables in this file
variable "az_resource_group_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}

# Load all nodes' config from the nodes.json file
variable "node_config_file" {
  description = "Path to the json file used to configure nodes"
  type        = string
  default     = "nodes.json" #TODO: remove after all tests complete
}

variable "node_container_port" {
  description = "Port exposed by the container instance to redirect traffic to"
  type        = number
  default     = 3000
}