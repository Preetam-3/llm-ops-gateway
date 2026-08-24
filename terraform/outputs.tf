output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.gateway.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.gateway.endpoint
}

output "gateway_release" {
  description = "Helm release name"
  value       = helm_release.gateway.name
}

output "gateway_namespace" {
  description = "Kubernetes namespace the gateway is deployed into"
  value       = helm_release.gateway.namespace
}

output "access_instructions" {
  description = "How to reach the gateway after apply"
  value = <<-EOT
    Gateway installed as Helm release "${helm_release.gateway.name}" in namespace "${helm_release.gateway.namespace}".

    Port-forward to try it locally:
      kubectl -n ${helm_release.gateway.namespace} port-forward svc/${helm_release.gateway.name}-gateway 8000:8000
      curl http://localhost:8000/health
  EOT
}