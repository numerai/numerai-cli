#output "aws_nodes" {
#  value = try(length(module.aws) > 0, false) ? jsondecode(jsonencode(module.aws[0].outputs)) : {}
#}

output "azure_nodes" {
  value = try(length(module.azure) > 0, false) ? jsondecode(jsonencode(module.azure[0].outputs)) : {}
}
