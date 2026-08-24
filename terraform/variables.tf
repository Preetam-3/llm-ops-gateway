variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the cluster"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "llm-ops-gateway"
}

variable "release_name" {
  description = "Helm release name"
  type        = string
  default     = "llm-gateway"
}

variable "namespace" {
  description = "Kubernetes namespace to deploy into"
  type        = string
  default     = "llm-gateway"
}

variable "machine_type" {
  description = "GKE node machine type"
  type        = string
  default     = "e2-standard-2"
}

variable "node_count" {
  description = "Initial node count"
  type        = number
  default     = 2
}

variable "min_nodes" {
  description = "Minimum node pool size"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Maximum node pool size"
  type        = number
  default     = 5
}

variable "gateway_image" {
  description = "Container image for the gateway (without tag)"
  type        = string
  default     = "ghcr.io/your-username/llm-ops-gateway"
}

variable "gateway_image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "groq_api_key" {
  description = "Groq API key (stored in a Kubernetes Secret)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gateway_api_key" {
  description = "Admin/client key for the gateway"
  type        = string
  sensitive   = true
  default     = "change-me"
}

variable "max_requests_per_minute" {
  description = "Rate limit per API key"
  type        = number
  default     = 30
}

variable "enable_autoscaling" {
  description = "Enable HPA autoscaling"
  type        = bool
  default     = true
}