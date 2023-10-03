resource "google_artifact_registry_repository" "registry" {
  count         = length(local.gcp_nodes) > 0 ? 1 : 0
  repository_id = "numerai-container-registry"
  format        = "DOCKER"
  depends_on = [
    google_project_service.artifact_registry,
    google_project_service.cloud_resource_manager
  ]
}

output "artifact_registry_details" {
  value = length(local.gcp_nodes) > 0 ? {
    registry_id = google_artifact_registry_repository.registry[0].id
  } : null
}
