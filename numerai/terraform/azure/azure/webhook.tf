# Azure Function App
# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_function

# Access existing Azure subscription under current IAM role
data "azurerm_subscription" "current" {}

data "azurerm_role_definition" "contributor" {
  name = "Contributor"
}

# Assign "Contributor" role of the Azure Resource Group to the Function App
resource "azurerm_role_assignment" "function_app" {
  for_each = { for name, config in var.nodes : name => config }
  scope               = azurerm_resource_group.rg[each.key].id # Limit scope to the submission node resource group
  role_definition_id = "${data.azurerm_subscription.current.id}${data.azurerm_role_definition.contributor.id}"
  principal_id       = azurerm_linux_function_app.function_app[each.key].identity[0].principal_id
}


# Define the service plan for the Function App
#Function consumption plan: https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale
resource "azurerm_service_plan" "function_app" {
  for_each = { for name, config in var.nodes : name => config }
  name                = "${local.node_prefix}-function-app-plan"
  resource_group_name = azurerm_resource_group.rg[each.key].name
  location            = azurerm_resource_group.rg[each.key].location
  os_type             = "Linux"
  sku_name            = "Y1" 
}

# Create storage account for the Function App
resource "azurerm_storage_account" "function_app" {
  for_each = { for name, config in var.nodes : name => config }
  name                     = "funcstorage${random_string.random[each.key].result}"
  resource_group_name      = azurerm_resource_group.rg[each.key].name
  location                 = azurerm_resource_group.rg[each.key].location

  account_tier             = "Standard"
  account_replication_type = "LRS"

}

resource "random_string" "random" {
  for_each = {for name, config in var.nodes : name => config }
  length  = 10
  lower = true
  upper = false
  special = false
}

# Create Linux Function App, with a azure_trigger Function
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators&tabs=wsgi%2Capplication-level#folder-structure
resource "azurerm_linux_function_app" "function_app" {
  for_each = { for name, config in var.nodes : name => config }
  #name                = "${local.node_prefix}-func-app"
  #name                = substr("${local.node_prefix}-trigger-${var.node_name}",-60, -1)
  name                = "http-trigger-${random_string.random[each.key].result}"
  resource_group_name = azurerm_resource_group.rg[each.key].name
  location            = azurerm_resource_group.rg[each.key].location
  service_plan_id            = azurerm_service_plan.function_app[each.key].id

  storage_account_name       = azurerm_storage_account.function_app[each.key].name
  storage_account_access_key = azurerm_storage_account.function_app[each.key].primary_access_key

  zip_deploy_file = "azure_trigger.zip"
  
  site_config {
    application_stack {
      python_version = "3.10"
    }

    application_insights_key   = azurerm_application_insights.app_insights[each.key].instrumentation_key
    application_insights_connection_string = azurerm_application_insights.app_insights[each.key].connection_string

  }
  
  # Add environment variables for the azure_trigger Function use
  # https://learn.microsoft.com/en-us/azure/app-service/reference-app-settings?tabs=kudu%2Cdotnet
  app_settings = {
    "AZURE_SUBSCRIPTION_ID" = data.azurerm_subscription.current.subscription_id
    "AZURE_RESOURCE_GRP_NAME" = azurerm_resource_group.rg[each.key].name
    "AZURE_CONTAINER_GRP_NAME" = azurerm_container_group.container[each.key].name
    "AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"
  }

  identity {
    type = "SystemAssigned"
  }
}

# Application insights to log function usage and errors 
resource "azurerm_application_insights" "app_insights" {
  for_each = { for name, config in var.nodes : name => config }
  name                = "func-app-application-insights-${random_string.random[each.key].result}"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  workspace_id        = azurerm_log_analytics_workspace.function_app[each.key].id
  application_type    = "other"
}

# Log analytics workspace to log function usage and errors 
resource "azurerm_log_analytics_workspace" "function_app" {
  for_each = { for name, config in var.nodes : name => config }
  name                = "func-app-log-analytics-${random_string.random[each.key].result}"
  location            = azurerm_resource_group.rg[each.key].location
  resource_group_name = azurerm_resource_group.rg[each.key].name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Cron trigger
# Define the service plan for the Function App
#Function consumption plan: https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale
resource "azurerm_service_plan" "cron_function_app" {
    for_each = { 
    for name, config in var.nodes : 
      name => lookup(config, "cron", null)
      if lookup(config, "cron", null) != null
  } 
  name                = "${local.node_prefix}-cron-func-app-plan"
  resource_group_name = azurerm_resource_group.rg[each.key].name
  location            = azurerm_resource_group.rg[each.key].location
  os_type             = "Linux"
  sku_name            = "Y1" 
}

resource "azurerm_linux_function_app" "cron_function_app" {
  for_each = { 
    for name, config in var.nodes : 
      name => lookup(config, "cron", null)
      if lookup(config, "cron", null) != null
  } 

  name                = "cron-trigger-${random_string.random[each.key].result}"
  resource_group_name = azurerm_resource_group.rg[each.key].name
  location            = azurerm_resource_group.rg[each.key].location
  service_plan_id            = azurerm_service_plan.cron_function_app[each.key].id

  storage_account_name       = azurerm_storage_account.function_app[each.key].name
  storage_account_access_key = azurerm_storage_account.function_app[each.key].primary_access_key

  zip_deploy_file = "azure_cron_trigger.zip"
  
  site_config {
    application_stack {
      python_version = "3.10"
    }

    application_insights_key   = azurerm_application_insights.app_insights[each.key].instrumentation_key
    application_insights_connection_string = azurerm_application_insights.app_insights[each.key].connection_string

  }
  
  # Add environment variables for the azure_trigger Function use
  # https://learn.microsoft.com/en-us/azure/app-service/reference-app-settings?tabs=kudu%2Cdotnet
  app_settings = {
    "CRON_EXPRESSION" = each.value
    "WEBHOOK_URL" = "https://${azurerm_linux_function_app.function_app[each.key].name}.azurewebsites.net/api/orchestrators/start_submission"
    "AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"
  }

  identity {
    type = "SystemAssigned"
  }
}