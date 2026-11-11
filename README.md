# Ashrith V: AI DevOps / SRE Portfolio

Hands-on projects in **AI DevOps, Cloud, SRE and Platform Engineering**. Each one is built and deployed the way production systems are: Infrastructure as Code, GitOps, keyless cloud security, CI/CD with security scanning, and full observability.

## Projects

### 1. [OpsPilot: AI runbook assistant on Azure](opspilot-azure/)
A RAG chatbot that answers on-call questions **only from your team's runbooks**, with source citations.

`AKS` `Azure OpenAI` `pgvector` `Terraform` `Helm` `Argo CD` `GitHub Actions` `Workload Identity` `Prometheus` `Grafana` `Python` `FastAPI`

- Retrieval-Augmented Generation with Azure OpenAI (gpt-4o-mini + text-embedding-3-small) and pgvector on Azure PostgreSQL
- Guardrails: prompt-injection blocking, "no runbook, no answer", secret redaction
- Keyless: AKS Workload Identity to Azure OpenAI (API keys disabled), GitHub OIDC to Azure
- LLM observability: latency, tokens, errors and retrieval quality in Grafana, with alert rules

### 2. [Incident Copilot: AI agent for Kubernetes incidents on AWS](incident-copilot-aws/)
When a Prometheus alert fires, an AI agent investigates pods, logs, events and metrics through **MCP tools** and writes a root-cause report.

`EKS` `Amazon Bedrock` `vLLM` `MCP` `Agentic AI` `Terraform` `IRSA` `Argo CD` `Alertmanager` `Prometheus` `Grafana` `Python`

- Tool-calling agent loop over an MCP server with read-only Kubernetes and PromQL tools
- Runs on Amazon Bedrock (Converse API) or a self-hosted open-source model on vLLM (GPU node)
- Safety: read-only RBAC, namespace allow-list, log redaction before the LLM, step budget, alert de-duplication
- GitOps app-of-apps: one command deploys monitoring, the agent and broken demo workloads

## Run them for free
Both projects include a **local mode with Docker Compose and Ollama**, so you can try them on a laptop without a cloud account. See each project's README.

## CI/CD
GitHub Actions workflows in [`.github/workflows`](.github/workflows) lint and test each app, validate Terraform and Helm, scan images with Trivy and, once cloud variables are configured, deploy through GitOps.

## About me
AI DevOps/SRE Engineer with 5+ years across Azure, AWS and GCP: Kubernetes (AKS, EKS, GKE, OpenShift), Terraform, GitHub Actions, observability and SRE practices.
[LinkedIn](https://www.linkedin.com/in/ashrith-v-426589407/)
