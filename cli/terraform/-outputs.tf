output "aws_applications" {
  value = jsondecode(jsonencode(module.aws[0].outputs))
}
