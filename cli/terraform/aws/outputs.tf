output "submission_url" {
  value = "${aws_api_gateway_deployment.app.invoke_url}/submit"
}

output "docker_repos" {
  value = {for i in range(length(var.applications)):
    var.applications[i].name => aws_ecr_repository.app[i].repository_url
  }
}
