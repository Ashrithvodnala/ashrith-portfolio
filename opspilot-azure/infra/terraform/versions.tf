terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # For a team setup, store state remotely, e.g.:
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
