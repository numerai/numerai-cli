output "outputs" {
  value = {for i in range(length(var.nodes)):
    var.nodes[i].name => {
      docker_repo = aws_ecr_repository.node[i].repository_url
      webhook_url = "${aws_api_gateway_deployment.node.invoke_url}/submit"
      cluster_log_group = aws_cloudwatch_log_group.ecs[i].name
      webhook_log_group = aws_cloudwatch_log_group.lambda.name
    }
  }
}
