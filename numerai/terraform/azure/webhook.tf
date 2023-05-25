# Azure Function App
# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_function

# TODO: Create system assigned identity for the function trigger
data "azurerm_subscription" "current" {}

#data "azurerm_role_definition" "contributor" {
#  name = "Contributor"
#}

# Assign "Contributor" role to the function app
# [ERROR:May 26] unable to acquire access token 
#resource "azurerm_role_assignment" "function_app" {
#  scope              = data.azurerm_subscription.current.id
#  role_definition_id = "${data.azurerm_subscription.current.id}${data.azurerm_role_definition.contributor.id}"
#  principal_id       = azurerm_linux_function_app.function_app.identity[0].principal_id
#}


# Define the service plan for the function app
resource "azurerm_service_plan" "function_app" {
  name                = "${local.node_prefix}-function-app-plan"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_storage_account" "function_app" {
  name                     = "numeraifunctionstorage" # TODO: append model name as prefix
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

}


resource "azurerm_linux_function_app" "function_app" {
  name                = "${local.node_prefix}-function-app"
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

  identity {
    type = "SystemAssigned"
  }
}


resource "azurerm_function_app_function" "function" {
  name            = "${local.node_prefix}-function-app-function"
  function_app_id = azurerm_linux_function_app.function_app.id
  language        = "Python"
  
  file {
    name    = "trigger_function.py"
    content = file("trigger_function.py")
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
        "name" = "req"
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