variable "aws_region" {
  description = "The AWS region to create things in."
  type        = string
  default     = "us-east-1"
}

variable "az_count" {
  description = "Number of AWS Available Zones to cover in a given AWS region"
  type        = string
  default     = "1"
}

variable "nodes" {
  description = "Map of node names to their configurations"
  type        = map(map(any))
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

variable "volume_size" {
  description = "Size of the EC2 volumes in GB"
  type        = number
  default     = 20
}