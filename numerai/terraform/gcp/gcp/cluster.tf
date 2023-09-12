resource "google_cloud_run_v2_job" "node" {
  for_each = { for name, config in var.nodes : name => config }

  location = var.gcp_region
  project  = var.project
  name     = replace(each.key, "_", "-")

  template {
    template {
      containers {
        image = "${var.gcp_region}-docker.pkg.dev/${var.project}/${var.registry_name}/${each.key}:latest"

        resources {
          limits = {
            memory = "16Gi"
            cpu    = "4000m"
          }
        }
      }
      timeout = "3600s"
    }
  }

  lifecycle {
    ignore_changes = [
      launch_stage,
    ]
  }
}
