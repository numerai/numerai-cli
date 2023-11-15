output "gcp_nodes" {
  value = try(length(module.gcp) > 0, false) ? jsondecode(jsonencode(module.gcp[0].outputs)) : {}
}
