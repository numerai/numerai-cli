
variable "node_config_file" {
  description = "Path to the json file used to configure nodes"
  type        = string
  default     = "nodes.json"
}

variable "node_container_port" {
  description = "Port exposed by the docker image to redirect traffic to"
  type        = number
  default     = 3000
}

## TODO: Add Azure related variables
variable "az_rg_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}