output "nodes" {
  value = try(length(module.azure) > 0, false) ? jsondecode(jsonencode(module.azure[0].outputs)) : {}
}


