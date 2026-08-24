# Terraform — GKE deployment

Provisions a Google Kubernetes Engine (GKE) cluster and deploys the
LLM Ops Gateway Helm chart into it.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- Google Cloud CLI (`gcloud`) authenticated:
  ```bash
  gcloud auth application-default login
  ```

## Usage

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — set project_id, image, and secrets

terraform init     # pulls providers
terraform plan     # preview the changes
terraform apply    # create the cluster + install the gateway
```

After `apply`, Terraform prints port-forward instructions for reaching
the gateway. In short:

```bash
kubectl -n llm-gateway port-forward svc/llm-gateway-gateway 8000:8000
curl http://localhost:8000/health
```

## Tearing down

```bash
terraform destroy
```

> Note: the deployed `gateway_api_key` and `groq_api_key` are stored in a
> Kubernetes Secret. Prefer `terraform.tfvars` over shell environment
> variables, and keep the file out of version control
> (it is listed in `.gitignore`).

## Tuning

| Variable | Default | Description |
|---|---|---|
| `machine_type` | `e2-standard-2` | Node machine type |
| `node_count` | `2` | Initial node count |
| `min_nodes` / `max_nodes` | `1` / `5` | Node pool autoscaling range |
| `enable_autoscaling` | `true` | HPA on the gateway deployment |
| `region` | `us-central1` | GCP region |