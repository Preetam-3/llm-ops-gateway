# Deployment

## Option 1: Docker Compose (local / self-hosted)

Boots the full stack — gateway, Redis, Prometheus, and Grafana — in one
command:

```bash
make run
```

```bash
make stop    # tear down
make logs    # follow service logs
```

Uses host networking; Prometheus listens on `:9091` and Grafana on `:4000`
to avoid port conflicts.

## Option 2: Kubernetes via Helm (production)

The `helm/` chart deploys the gateway plus Redis, Prometheus, and Grafana.

```bash
minikube start
helm install llm-gateway ./helm/
kubectl port-forward svc/llm-gateway-gateway 8000:8000
kubectl port-forward svc/llm-gateway-grafana 4000:3000
```

Set your keys at install time:

```bash
helm install llm-gateway ./helm/ \
  --set secrets.groqApiKey=gsk_your_key \
  --set secrets.gatewayApiKey=your-admin-key \
  --set image.repository=ghcr.io/your-username/llm-ops-gateway
```

### Production hardening built into the chart

- **Resource requests/limits** on the gateway (`resources` in `values.yaml`)
- **HorizontalPodAutoscaler** — CPU/memory based autoscaling
  (`autoscaling.*`)
- **PodDisruptionBudget** — guarantees minimum availability during
  voluntary disruptions (`pdb.*`)
- **Liveness/readiness probes** wired to `/health`
- **Secrets** rendered from `values.yaml` (or use `secrets.existingSecret`
  to reference your own)

## Option 3: Cloud via Terraform (GKE)

The `terraform/` directory provisions a GKE cluster and installs the Helm
chart.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

See `terraform/README.md` for full instructions.

## Options compared

| | Compose | Helm | Terraform |
|---|---|---|---|
| Use case | Local dev | On-prem / any cluster | Managed cloud (GKE) |
| Effort | One command | One helm install | `plan` → `apply` |
| Autoscaling | — | HPA | HPA + node pool autoscaling |
| Cost tracking | ✗ | ✗ | ~$ for cluster nodes |

## Upgrading

```bash
# Docker Compose
docker compose pull && docker compose up -d

# Helm
helm upgrade llm-gateway ./helm/ --reuse-values

# Terraform
cd terraform && terraform plan && terraform apply
```

## Backups

SQLite data (`gateway.db`) is the only state you need to protect locally.
In Kubernetes, add a PersistentVolumeClaim if you want history to survive
pod rescheduling (see the `database_path` setting).