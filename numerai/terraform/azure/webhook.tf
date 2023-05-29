# Azure Function App
# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_function

# Access existing Azure subscription under current IAM role
data "azurerm_subscription" "current" {}

data "azurerm_role_definition" "contributor" {
  name = "Contributor"
}

# Assign "Contributor" role of the Azure Resource Group to the Function App
resource "azurerm_role_assignment" "function_app" {
  scope               = azurerm_resource_group.rg.id # Limit scope to the submission node resource group
  role_definition_id = "${data.azurerm_subscription.current.id}${data.azurerm_role_definition.contributor.id}"
  principal_id       = azurerm_linux_function_app.function_app.identity[0].principal_id
}


# Define the service plan for the Function App
#Function consumption plan: https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale
resource "azurerm_service_plan" "function_app" {
  name                = "${local.node_prefix}-function-app-plan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1" 
}
# Create storage account for the Function App
resource "azurerm_storage_account" "function_app" {
  name                     = "numeraifunctionstorage" # TODO: append model name as prefix
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

}

# Create Linux Function App, with a azure_trigger Function
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators&tabs=wsgi%2Capplication-level#folder-structure
resource "azurerm_linux_function_app" "function_app" {
  name                = "${local.node_prefix}-func-app"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.function_app.id

  storage_account_name       = azurerm_storage_account.function_app.name
  storage_account_access_key = azurerm_storage_account.function_app.primary_access_key

  zip_deploy_file = "azure_trigger.zip"
  
  site_config {
    application_stack {
      python_version = "3.9"
    }

    application_insights_key   = azurerm_application_insights.app_insights.instrumentation_key
    application_insights_connection_string = azurerm_application_insights.app_insights.connection_string

  }
  
  # Add environment variables for the azure_trigger Function use
  # https://learn.microsoft.com/en-us/azure/app-service/reference-app-settings?tabs=kudu%2Cdotnet
  app_settings = {
    "AZURE_SUBSCRIPTION_ID" = data.azurerm_subscription.current.subscription_id
    "AZURE_RESOURCE_GRP_NAME" = azurerm_resource_group.rg.name
    "AZURE_CONTAINER_GRP_NAME" = azurerm_container_group.container.name

  }

  identity {
    type = "SystemAssigned"
  }
}

#https://tf-numerai-submission-func-app.azurewebsites.net/api/azure_trigger

# Application insights to log function usage and errors
resource "azurerm_application_insights" "app_insights" {
  name                = "func-app-application-insights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "other"
}

resource "azurerm_log_analytics_workspace" "function_app" {
  name                = "func-app-log-analytics"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
