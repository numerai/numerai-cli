# Azure Function App
# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_function

# Access existing Azure subscription under current IAM role
data "azurerm_subscription" "current" {}

data "azurerm_role_definition" "contributor" {
  name = "Contributor"
}

# Assign "Contributor" role of the Azure Resource Group to the function app
resource "azurerm_role_assignment" "function_app" {
  #scope              = data.azurerm_subscription.current.id 
  scope               = azurerm_resource_group.rg.id # Limit scope to the current resource group
  role_definition_id = "${data.azurerm_subscription.current.id}${data.azurerm_role_definition.contributor.id}"
  principal_id       = azurerm_linux_function_app.function_app.identity[0].principal_id
}


# Define the service plan for the function app
resource "azurerm_service_plan" "function_app" {
  name                = "${local.node_prefix}-function-app-plan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1" #Function consumption plan: https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale
}

resource "azurerm_storage_account" "function_app" {
  name                     = "numeraifunctionstorage" # TODO: append model name as prefix
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

}


resource "azurerm_linux_function_app" "function_app" {
  name                = "${local.node_prefix}-func-app"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.function_app.id

  storage_account_name       = azurerm_storage_account.function_app.name
  storage_account_access_key = azurerm_storage_account.function_app.primary_access_key

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }
  
  # Add environment variables for azure_webhook.py use
  # https://learn.microsoft.com/en-us/azure/app-service/reference-app-settings?tabs=kudu%2Cdotnet
  app_settings = {
    "AZURE_SUBSCRIPTION_ID" = "${data.azurerm_subscription.current.id}"
    "AZURE_RESOURCE_GRP_NAME" = "${azurerm_resource_group.rg.name}"
    "AZURE_CONTAINER_GRP_NAME" = "${azurerm_container_group.container.name}"
  }

  identity {
    type = "SystemAssigned"
  }
}


resource "azurerm_function_app_function" "function" {
  name            = "${local.node_prefix}-function"
  function_app_id = azurerm_linux_function_app.function_app.id
  language        = "Python"
  
  file {
    #name    = "azure_webhook.py"
    #content = file("azure_webhook.py")

    name    = "azure_function.zip"
    content = file("azure_function.zip")
  }

  test_data = jsonencode({
    "name" = "Azure"
  })

  # "authLevel" = "function"
  config_json = jsonencode({
    "bindings" = [
      {
        "authLevel" = "anonymous"
        "direction" = "in"
        "methods" = [
          "get",
          "post",
        ]
        "name" = "predict"
        "type" = "httpTrigger"
      },
      {
        "direction" = "out"
        "name"      = "$return"
        "type"      = "http"
      },
    ]
  })
}

# Application insights to log function usage and errors
resource "azurerm_application_insights" "app_insights" {
  name                = "tf-test-appinsights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "other"
}

resource "azurerm_log_analytics_workspace" "function_app" {
  name                = "tf-test-log-analytics"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

#output "instrumentation_key" {
#  value = azurerm_application_insights.app_insights.instrumentation_key
#}

#output "app_id" {
#  value = azurerm_application_insights.app_insights.app_id
#}