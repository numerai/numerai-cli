output "outputs" {
  value = {for i in range(length(var.applications)):
    var.applications[i].name => {
      docker_repo = aws_ecr_repository.app[i].repository_url
      webhook_url = "${aws_api_gateway_deployment.app.invoke_url}/submit"
      cluster_log_group = aws_cloudwatch_log_group.ecs[i].name
      webhook_log_group = aws_cloudwatch_log_group.lambda.name
    }
  }
}
