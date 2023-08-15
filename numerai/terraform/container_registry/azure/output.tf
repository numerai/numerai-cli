output "acr_repo_details" {
  value = {
    registry_rg_name = azurerm_resource_group.acr_rg.name
    registry_name    = azurerm_container_registry.registry.name
    acr_login_server = azurerm_container_registry.registry.login_server
  }
}
