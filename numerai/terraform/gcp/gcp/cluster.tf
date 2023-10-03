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
            memory = "${each.value.memory / 1024}Gi"
            cpu    = "${1000 * each.value.cpu / 1024}m"
          }
        }
      }
      timeout     = "${each.value.timeout_minutes * 60}s"
      max_retries = 0
    }
  }

  lifecycle {
    ignore_changes = [
      launch_stage,
    ]
  }
}
