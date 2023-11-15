variable "gcp_region" {
  description = "The GCP region to create things in."
  type        = string
  default     = "us-east1"
}

variable "project" {
  description = "The project to create things in"
}

variable "nodes" {
  description = "Map of node names to their configurations"
  type        = map(map(any))
}

variable "registry_name" {
  description = "The name of the registry where containers for this project are stored"
}
