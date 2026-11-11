variable "subscription_id" {
  description = "Azure subscription ID (az account show --query id -o tsv)"
  type        = string
}

variable "prefix" {
  description = "Short name used in every resource name"
  type        = string
  default     = "opspilot"
}

variable "location" {
  description = "Region for AKS, ACR and PostgreSQL"
  type        = string
  default     = "eastus2"
}

variable "openai_location" {
  description = "Region for Azure OpenAI (pick one where your chosen models are available)"
  type        = string
  default     = "eastus2"
}

variable "node_vm_size" {
  description = "AKS node size. B-series keeps the demo cheap."
  type        = string
  default     = "Standard_B2s"
}

variable "node_count" {
  type    = number
  default = 2
}

variable "chat_model" {
  description = "Azure OpenAI chat model and version"
  type        = object({ name = string, version = string })
  default     = { name = "gpt-4o-mini", version = "2024-07-18" }
}

variable "embedding_model" {
  description = "Azure OpenAI embedding model and version (text-embedding-3-small = 1536 dimensions)"
  type        = object({ name = string, version = string })
  default     = { name = "text-embedding-3-small", version = "1" }
}

variable "github_repo" {
  description = "GitHub repo allowed to push images, as owner/name"
  type        = string
  default     = "Ashrithvodnala/ashrith-portfolio"
}

variable "app_namespace" {
  type    = string
  default = "opspilot"
}

variable "tags" {
  type    = map(string)
  default = { project = "opspilot", owner = "ashrith", purpose = "portfolio" }
}
