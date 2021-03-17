output "outputs" {
  value = {for node, config in var.nodes:
    node => {
      docker_repo = aws_ecr_repository.node[node].repository_url
      webhook_url = "${aws_apigatewayv2_api.submit.api_endpoint}/predict${split(" ", aws_apigatewayv2_route.submit[node].route_key)[1]}"
      cluster_log_group = aws_cloudwatch_log_group.ecs[node].name
      webhook_log_group = aws_cloudwatch_log_group.lambda[node].name
    }
  }
}
