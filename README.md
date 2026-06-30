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

- Docker
- Minikube
- Helm 3.15+
- Python 3.11+
- [Groq API key](https://console.groq.com) (free)

### Setup

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — set GROQ_API_KEY and GATEWAY_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Minikube
minikube start

# 4. Deploy the full stack
helm install llm-gateway ./helm/

# 5. Port-forward the gateway
kubectl port-forward svc/llm-gateway-gateway 8000:8000 &

# 6. Chat!
python chat.py "What is Docker?"
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
├── app/              # FastAPI gateway application
├── helm/             # Kubernetes Helm chart
├── prometheus/       # Prometheus scrape config
├── grafana/          # Grafana dashboard JSON
├── tests/            # Pytest test suite
├── ui/               # Optional chat UI (HTML/JS)
├── chat.py           # CLI client
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
