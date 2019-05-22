output "submission_url" {
  value = "${aws_api_gateway_deployment.app.invoke_url}/submit"
}

output "docker_repo" {
  value = "${aws_ecr_repository.app.repository_url}"
}
