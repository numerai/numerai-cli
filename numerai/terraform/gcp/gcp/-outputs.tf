output "outputs" {
  value = { for node, config in var.nodes :
    node => {
      docker_repo = "${var.gcp_region}-docker.pkg.dev/${var.project}/${var.registry_name}/${node}"
      webhook_url = google_cloudfunctions_function.webhook[node].https_trigger_url
    }
  }
}
