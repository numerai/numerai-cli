output "outputs" {
  value = { for node, config in var.nodes :
    node => {
      docker_repo       = aws_ecr_repository.node[node].repository_url
      webhook_url       = aws_lambda_function_url.submission[node].function_url
      cluster_log_group = aws_cloudwatch_log_group.ecs[node].name
      webhook_log_group = aws_cloudwatch_log_group.lambda[node].name
      cluster_arn       = aws_batch_compute_environment.node.ecs_cluster_arn
    }
  }
}
