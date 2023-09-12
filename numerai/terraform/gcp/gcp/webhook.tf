resource "google_storage_bucket" "webhook" {
  for_each = { for name, config in var.nodes : name => config }
  name     = replace(each.key, "_", "-")
  project  = var.project
  location = var.gcp_region
}

resource "google_storage_bucket_object" "webhook" {
  for_each = { for name, config in var.nodes : name => config }
  name     = "index.${filemd5("cloud-function.zip")}.zip"
  bucket   = google_storage_bucket.webhook[each.key].name
  source   = "cloud-function.zip"
}

resource "google_cloudfunctions_function" "webhook" {
  for_each = { for name, config in var.nodes : name => config }
  project  = var.project
  name     = replace(each.key, "_", "-")

  runtime               = "python39"
  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.webhook[each.key].name
  source_archive_object = google_storage_bucket_object.webhook[each.key].name
  trigger_http          = true
  entry_point           = "run_job"
  environment_variables = {
    PROJECT  = var.project
    LOCATION = var.gcp_region
    JOB      = replace(each.key, "_", "-")
  }
}

resource "google_cloudfunctions_function_iam_binding" "webhook" {
  for_each       = { for name, config in var.nodes : name => config }
  project        = var.project
  cloud_function = google_cloudfunctions_function.webhook[each.key].name
  role           = "roles/cloudfunctions.invoker"
  members = [
    "allUsers",
  ]
}
