output "aws_nodes" {
  value = try(length(module.aws) > 0, false)
    ? jsondecode(jsonencode(module.aws[0].outputs))
    : {}
}
