output "aws_nodes" {
  value = jsondecode(jsonencode(module.aws[0].outputs))
}
