output "aws_nodes" {
  value = length(module.aws) > 0 ? jsondecode(jsonencode(module.aws[0].outputs)) : {}
}
