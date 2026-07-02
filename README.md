# LLM Ops Gateway

A production-grade API gateway for LLMs with real-time Prometheus observability — token usage, latency percentiles, cost-per-request, and error rates — deployed on Kubernetes with Helm and managed via GitHub Actions CI.

## Architecture

```
┌──────────┐     POST /v1/chat     ┌──────────────┐     OpenAI-compatible    ┌──────────┐
│  chat.py  │ ──────────────────►  │  FastAPI GW   │ ──────────────────────► │ Groq API │
│ (CLI)     │ ◄──────────────────  │  (K8s Pod)    │ ◄────────────────────── │ (LLM)    │
└──────────┘     LLM reply        └──────┬───────┘                         └──────────┘
                                         │
                              ┌──────────┴──────────┐
                              │  Prometheus (scrape) │
                              │  /metrics :8000      │
                              └──────────┬───────────┘
                                         │
                                    ┌────▼────┐
                                    │ Grafana │
                                    │ Dashbd  │
                                    └─────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- [Groq API key](https://console.groq.com) (free)

### Setup & Run

```bash
# 1. Clone and set up (one command does everything)
chmod +x setup.sh && ./setup.sh

# 2. Boot the full stack
make run

# 3. Chat!
./chat.py "What is Docker?"

# 4. Open Grafana dashboard
# http://localhost:4000 (login: admin / admin)

# 5. Stop when done
make stop
```

That's it. No Minikube, no Helm, no Kubernetes needed for local development.
The `make run` command starts the gateway, Redis, Prometheus, and Grafana with one command via Docker Compose.

### Kubernetes Deployment (Alternative)

For production-style deployment:

```bash
minikube start
helm install llm-gateway ./helm/
kubectl port-forward svc/llm-gateway-gateway 8000:8000 &
kubectl port-forward svc/llm-gateway-grafana 4000:3000 &
```

### Grafana Dashboard

```bash
kubectl port-forward svc/llm-gateway-grafana 4000:3000 &
# Open http://localhost:4000 (login: admin / admin)
```

### Chat UI (Optional)

Visit http://localhost:8000 after port-forwarding.

## Metrics Collected

| Metric | Type | Description |
|---|---|---|
| `llm_request_total` | Counter | Requests by model and status (success/error) |
| `llm_request_duration_seconds` | Histogram | Latency with p50/p95/p99 percentiles |
| `llm_tokens_total` | Counter | Prompt and completion tokens |
| `llm_estimated_cost_dollars` | Gauge | Per-request cost estimate |
| `llm_rate_limited_total` | Counter | Rate-limited request count |

## Project Structure

```
├── app/                 # FastAPI gateway application
├── helm/                # Kubernetes Helm chart
├── prometheus/          # Prometheus scrape config
├── grafana/             # Grafana dashboard + provisioning configs
├── tests/               # Pytest test suite
├── ui/                  # Optional chat UI (HTML/JS)
├── chat.py              # CLI client
├── docker-compose.yml   # Local dev stack (one command)
├── Makefile             # Common commands
├── setup.sh             # Bootstrap script
├── Dockerfile
└── requirements.txt
```

## Tech Stack

**Gateway:** Python 3.11, FastAPI, httpx, Uvicorn  
**Observability:** Prometheus, Grafana, prometheus-client  
**Rate Limiting:** Redis (token bucket)  
**LLM Provider:** Groq API (free, OpenAI-compatible)  
**Infrastructure:** Docker, Minikube, Helm  
**CI/CD:** GitHub Actions, GitHub Container Registry
