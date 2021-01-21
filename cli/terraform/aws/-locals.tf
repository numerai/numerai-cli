locals {
  app_prefix = "numerai-submission"
  app_names = flatten([for app in var.applications: [
    "${local.app_prefix}-${app.name}"
  ]])
}
