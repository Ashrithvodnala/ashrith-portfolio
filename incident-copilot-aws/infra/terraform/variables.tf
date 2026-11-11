variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "incident-copilot"
}

variable "kubernetes_version" {
  description = "EKS version. Use one that is in standard support (check the EKS docs)."
  type        = string
  default     = "1.34"
}

variable "node_instance_type" {
  type    = string
  default = "t3.large"
}

variable "enable_gpu_nodes" {
  description = "Add a GPU node group (g5.xlarge) for vLLM. Costs about $1/hour while running."
  type        = bool
  default     = false
}

variable "github_repo" {
  description = "GitHub repo allowed to push images, as owner/name"
  type        = string
  default     = "Ashrithvodnala/ashrith-portfolio"
}

variable "create_github_oidc_provider" {
  description = "Set false if your AWS account already has the GitHub OIDC provider"
  type        = bool
  default     = true
}

variable "app_namespace" {
  type    = string
  default = "copilot"
}

variable "tags" {
  type    = map(string)
  default = { project = "incident-copilot", owner = "ashrith", purpose = "portfolio" }
}
