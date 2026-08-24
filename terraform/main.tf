terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
  }
  required_version = ">= 1.5"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "default" {}

provider "kubernetes" {
  host                   = "https://${google_container_cluster.gateway.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.gateway.master_auth[0].cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = "https://${google_container_cluster.gateway.endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.gateway.master_auth[0].cluster_ca_certificate)
  }
}

# ── Cluster ──────────────────────────────────────────────

resource "google_container_cluster" "gateway" {
  name                     = var.cluster_name
  location                 = var.region
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = "default"
  subnetwork = "default"

  # Autopilot alternative: set `enable_autopilot = true` instead of a node pool.
  deletion_protection = false
}

resource "google_container_node_pool" "gateway_nodes" {
  name       = "gateway-pool"
  location   = var.region
  cluster    = google_container_cluster.gateway.name
  node_count = var.node_count

  node_config {
    machine_type = var.machine_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    labels = {
      "app" = "llm-ops-gateway"
    }
  }

  autoscaling {
    min_node_count = var.min_nodes
    max_node_count = var.max_nodes
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ── Gateway Helm release ─────────────────────────────────

resource "helm_release" "gateway" {
  name             = var.release_name
  chart            = "../helm"
  namespace        = var.namespace
  create_namespace = true
  wait             = true
  timeout          = 600

  set {
    name  = "image.repository"
    value = var.gateway_image
  }
  set {
    name  = "image.tag"
    value = var.gateway_image_tag
  }
  set {
    name  = "secrets.groqApiKey"
    value = var.groq_api_key
  }
  set {
    name  = "secrets.gatewayApiKey"
    value = var.gateway_api_key
  }
  set {
    name  = "config.maxRequestsPerMinute"
    value = var.max_requests_per_minute
  }
  set {
    name  = "autoscaling.enabled"
    value = var.enable_autoscaling
  }
}