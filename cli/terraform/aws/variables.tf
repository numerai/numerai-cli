variable "aws_region" {
  description = "The AWS region to create things in."
  type        = string
  default     = "us-east-1"
}

variable "az_count" {
  description = "Number of AZs to cover in a given AWS region"
  type        = string
  default     = "1"
}

variable "applications" {
  description = "Names of apps to deploy"
  type        = list(object({
    provider: string,
    name: string,
    cpu: number,
    memory: number,
  }))
}

variable "app_port" {
  description = "Port exposed by the docker image to redirect traffic to"
  type        = number
  default     = 3000
}

variable "gateway_stage_path" {
  description = "The prefixed path for the api gateway"
  type        = string
  default     = "v1"
}
