output "node_config" {
#https://tf-numerai-submission-func-app.azurewebsites.net/api/azure_trigger
#webhook_url = azurerm_function_app_function.function.invocation_url
#webhook_url = azurerm_linux_function_app.function_app.outbound_ip_addresses
  value={
    #docker_repo = var.image_url
    #docker_repo = "${azurerm_container_registry.registry.login_server}/${var.model_name}"
    #resource_group_name = azurerm_resource_group.rg.name
    #registry_name = azurerm_container_registry.registry.name
    #acr_login_server = azurerm_container_registry.registry.login_server
    # docker_repo=, will be added during "node config", defining here will cause error in ACR creation
    #webhook_url = "https://${azurerm_linux_function_app.function_app.name}.azurewebsites.net/api/azure_trigger" 
    #webhook_log_group = azurerm_application_insights.app_insights.name
    docker_repo = local.node_config[var.node_name].docker_repo
    webhook_url = "https://${azurerm_linux_function_app.function_app.name}.azurewebsites.net/api/orchestrators/start_submission"
    webhook_log_group = azurerm_log_analytics_workspace.function_app.workspace_id
    cluster_log_group = azurerm_log_analytics_workspace.container_instance.workspace_id
  }

  #value = {for node, config in var.nodes:
  #node => {
  #  #docker_repo = aws_ecr_repository.node[node].repository_url
  #  webhook_url = "${aws_apigatewayv2_api.submit.api_endpoint}/predict${split(" ", aws_apigatewayv2_route.submit[node].route_key)[1]}"
  #  cluster_log_group = aws_cloudwatch_log_group.ecs[node].name
  #  webhook_log_group = aws_cloudwatch_log_group.lambda[node].name
  #  api_log_group = aws_cloudwatch_log_group.gateway.name
  #  }
  #}
}


#output "acr_repo_details" {
#  value={
#    acr_repo = azurerm_container_registry.registry.login_server
#    acr_repo_admin_username=azurerm_container_registry.registry.admin_username
#    acr_repo_admin_password=azurerm_container_registry.registry.admin_password
#  }
#  sensitive  = true
#}


