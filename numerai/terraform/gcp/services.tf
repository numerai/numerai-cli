resource "google_project_service" "cloud_resource_manager" {
  service = "cloudresourcemanager.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
}

resource "google_project_service" "artifact_registry" {
  service = "artifactregistry.googleapis.com"

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
  depends_on                 = [google_project_service.cloud_resource_manager]
}

resource "google_project_service" "storage" {
  service = "storage.googleapis.com"
  project = split("/", google_project_service.cloud_resource_manager.id)[0]

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
}

resource "google_project_service" "cloudfunctions" {
  service = "cloudfunctions.googleapis.com"
  project = split("/", google_project_service.cloud_resource_manager.id)[0]

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
}

resource "google_project_service" "cloudbuild" {
  service = "cloudbuild.googleapis.com"
  project = split("/", google_project_service.cloud_resource_manager.id)[0]

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
}

resource "google_project_service" "workflows" {
  service = "workflows.googleapis.com"
  project = split("/", google_project_service.cloud_resource_manager.id)[0]

  timeouts {
    create = "30m"
    update = "40m"
  }

  disable_dependent_services = true
}
