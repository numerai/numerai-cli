terraform {
  required_version = "1.5.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">=4.79"
    }
  }
}

# Specify the provider and access details
provider "google" {
  region = var.region
}

locals {
  nodes = jsondecode(file(var.node_config_file))
  gcp_nodes = {
    for node, config in local.nodes :
    node => config if config.provider == "gcp"
  }
}

module "gcp" {
  count         = length(local.gcp_nodes) > 0 ? 1 : 0
  source        = "./gcp"
  gcp_region    = var.region
  nodes         = local.gcp_nodes
  project       = split("/", google_project_service.cloud_resource_manager.id)[0]
  registry_name = google_artifact_registry_repository.registry[0].name
  depends_on = [
    google_project_service.artifact_registry,
    google_project_service.cloudbuild,
    google_project_service.cloudfunctions,
    google_project_service.storage
  ]
}
