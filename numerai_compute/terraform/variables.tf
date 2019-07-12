variable "aws_region" {
  description = "The AWS region to create things in."
  default     = "us-east-1"
}

variable "az_count" {
  description = "Number of AZs to cover in a given AWS region"
  default     = "1"
}

variable "app_name" {
  description = "Name of app"
  default     = "numerai-submission"
}

variable "app_port" {
  description = "Port exposed by the docker image to redirect traffic to"
  default     = 3000
}

variable "gateway_stage_path" {
  description = "The prefixed path for the api gateway"
  default     = "v1"
}

variable "fargate_cpu" {
  description = "Fargate instance CPU units to provision (1 vCPU = 1024 CPU units)"
  default     = "2048"
}

variable "fargate_memory" {
  description = "Fargate instance memory to provision (in MiB)"
  default     = "16384"
}
