output "resource_group" { value = azurerm_resource_group.rg.name }
output "aks_name" { value = azurerm_kubernetes_cluster.aks.name }
output "get_credentials" {
  value = "az aks get-credentials -g ${azurerm_resource_group.rg.name} -n ${azurerm_kubernetes_cluster.aks.name}"
}
output "acr_login_server" { value = azurerm_container_registry.acr.login_server }
output "acr_name" { value = azurerm_container_registry.acr.name }
output "openai_endpoint" { value = azurerm_cognitive_account.openai.endpoint }
output "chat_deployment" { value = azurerm_cognitive_deployment.chat.name }
output "embedding_deployment" { value = azurerm_cognitive_deployment.embedding.name }
output "app_identity_client_id" { value = azurerm_user_assigned_identity.app.client_id }
output "github_client_id" { value = azurerm_user_assigned_identity.github.client_id }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
output "subscription_id" { value = var.subscription_id }
output "postgres_host" { value = azurerm_postgresql_flexible_server.pg.fqdn }
output "database_url" {
  value     = "postgresql://opspilot:${random_password.pg.result}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/opspilot?sslmode=require"
  sensitive = true
}
