data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  name = "${var.prefix}-${random_string.suffix.result}"
  # ACR names: letters and numbers only
  acr_name = replace("${var.prefix}${random_string.suffix.result}acr", "-", "")
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = var.tags
}

# ---------- Logging ----------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ---------- Container registry ----------
resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = var.tags
}

# ---------- AKS ----------
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = local.name

  oidc_issuer_enabled       = true # needed for workload identity
  workload_identity_enabled = true

  default_node_pool {
    name       = "system"
    vm_size    = var.node_vm_size
    node_count = var.node_count
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  }

  tags = var.tags
}

# Let AKS pull images from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# ---------- Azure OpenAI ----------
resource "azurerm_cognitive_account" "openai" {
  name                  = "aoai-${local.name}"
  location              = var.openai_location
  resource_group_name   = azurerm_resource_group.rg.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "aoai-${local.name}"
  local_auth_enabled    = false # keyless only: apps must use Microsoft Entra ID
  tags                  = var.tags
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.chat_model.name
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = var.chat_model.name
    version = var.chat_model.version
  }
  sku {
    name     = "GlobalStandard"
    capacity = 10 # thousands of tokens per minute
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_model.name
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = var.embedding_model.name
    version = var.embedding_model.version
  }
  sku {
    name     = "Standard"
    capacity = 10
  }
  depends_on = [azurerm_cognitive_deployment.chat] # Azure deploys models one at a time
}

# ---------- Workload identity for the app (keyless access to Azure OpenAI) ----------
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.name}-app"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "app" {
  name      = "aks-${var.app_namespace}"
  parent_id = azurerm_user_assigned_identity.app.id
  issuer    = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  subject   = "system:serviceaccount:${var.app_namespace}:opspilot"
  audience  = ["api://AzureADTokenExchange"]
}

resource "azurerm_role_assignment" "app_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# ---------- PostgreSQL with pgvector ----------
resource "random_password" "pg" {
  length  = 24
  special = false
}

resource "azurerm_postgresql_flexible_server" "pg" {
  name                          = "pg-${local.name}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  version                       = "16"
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  administrator_login           = "opspilot"
  administrator_password        = random_password.pg.result
  public_network_access_enabled = true # demo only; use private networking in production
  tags                          = var.tags

  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.pg.id
  value     = "VECTOR"
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "opspilot"
  server_id = azurerm_postgresql_flexible_server.pg.id
}

# Allow traffic from Azure services (AKS). Demo setting.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ---------- GitHub Actions: keyless login with OIDC ----------
resource "azurerm_user_assigned_identity" "github" {
  name                = "id-${local.name}-github"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "github_main" {
  name      = "github-main"
  parent_id = azurerm_user_assigned_identity.github.id
  issuer    = "https://token.actions.githubusercontent.com"
  subject   = "repo:${var.github_repo}:ref:refs/heads/main"
  audience  = ["api://AzureADTokenExchange"]
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}
