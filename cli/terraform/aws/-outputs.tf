output "outputs" {
  value = {for i in range(length(var.nodes)):
    var.nodes[i].name => {
      docker_repo = aws_ecr_repository.node[i].repository_url
      webhook_url = "${aws_apigatewayv2_api.node.api_endpoint}${split(" ", aws_apigatewayv2_route.submit[i].route_key)[1]}"
      cluster_log_group = aws_cloudwatch_log_group.ecs[i].name
      webhook_log_group = aws_cloudwatch_log_group.lambda.name
    }
  }
}
