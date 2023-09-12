variable "region" {
  description = "The GCP region to create things in."
  type        = string
  default     = "us-east1"
}

variable "node_config_file" {
  description = "Path to the json file used to configure nodes"
  type        = string
  default     = "nodes.json"
}
