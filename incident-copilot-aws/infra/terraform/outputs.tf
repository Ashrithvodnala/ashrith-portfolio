output "cluster_name" { value = module.eks.cluster_name }
output "update_kubeconfig" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
output "ecr_repository_url" { value = aws_ecr_repository.app.repository_url }
output "copilot_role_arn" { value = module.copilot_irsa.iam_role_arn }
output "github_actions_role_arn" { value = aws_iam_role.github.arn }
output "region" { value = var.region }
