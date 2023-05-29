# Store all terraform variables in this file
variable "az_resource_group_location" {
  description = "Default location of the Azure resource group."
  type        = string
  default     = "eastus"
}

# Put into locals
#variable "az_resource_group_prefix" {
#  default     = "numerai"
#  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
#}

# Followings are referencing aws version
variable "node_config_file" {
  description = "Path to the json file used to configure nodes"
  type        = string
  default     = "abcabc" #TODO: remove to load the .numerai config files
}

variable "node_container_port" {
  description = "Port exposed by the container instance to redirect traffic to"
  type        = number
  default     = 3000
}