variable "region" {
  description = "The AWS region to create things in."
  type        = string
  default     = "us-east-1"
}

variable "az_count" {
  description = "Number of AZs to cover in a given region"
  type        = string
  default     = "1"
}

variable "node_config_file" {
  description = "Path to the json file used to configure applications"
  type        = string
}

variable "node_container_port" {
  description = "Port exposed by the docker image to redirect traffic to"
  type        = number
  default     = 3000
}

variable "gateway_stage_path" {
  description = "The prefixed path for the api gateway"
  type        = string
  default     = "v1"
}
