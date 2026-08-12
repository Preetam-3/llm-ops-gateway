# LLM Ops Gateway

A self-hosted API gateway for LLMs with built-in monitoring — track requests, latency, token usage, cost, and rate limits through a live Grafana dashboard.

Works with any OpenAI-compatible provider (Groq, OpenAI, etc.). Runs locally with one command.

## Demo

![Demo GIF](assets/demo-optimized.gif)

> *Dashboard showing real-time request metrics, latency percentiles, token usage, and cost tracking.*

---

## How It Works

You talk to LLMs through this gateway instead of calling them directly. The gateway forwards your request, collects metrics along the way, and stores them in Prometheus — which Grafana visualizes.

```
             ┌──────────────────────────────────────────────────┐
             │              Your Machine (localhost)             │
             │                                                   │
  ./chat.py  │   ┌──────────┐   POST /chat     ┌──────────┐     │   ┌─────────┐
  "hello"    │   │ Gateway  │ ───────────────► │ Groq API │     │   │  LLM    │
   ──────►   │   │ :8000    │ ◄─────────────── │ (cloud)  │─────┼──►│  Model  │
  reply ◄── │   └────┬─────┘    response       └──────────┘     │   └─────────┘
             │         │                                          │
             │   ┌─────▼──────┐   queries    ┌──────────┐        │
             │   │ Prometheus │ ◄──────────  │ Grafana  │        │
             │   │ :9091      │ ──────────►  │ :4000    │        │
             │   └────────────┘   metrics    └──────────┘        │
             └──────────────────────────────────────────────────┘
```

**The flow:**
1. `chat.py` sends your message to the Gateway
2. Gateway forwards it to Groq API (or any LLM provider)
3. Gateway records: latency, tokens used, cost, success/error
4. Prometheus scrapes these metrics every 5 seconds
5. Grafana shows everything on a live dashboard

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- A free [Groq API key](https://console.groq.com)

### Setup

```bash
# One-command setup (creates .env, installs Python deps)
chmod +x setup.sh && ./setup.sh

# Edit .env and add your Groq API key
#   GROQ_API_KEY=gsk_your_key_here
```

### Run

```bash
# Boot everything: Gateway + Redis + Prometheus + Grafana
make run

# Chat with the model
./chat.py "What is Docker?"

# Open the dashboard
#   http://localhost:4000    (Grafana — login: admin / admin)
#   http://localhost:8000    (Gateway API)

# Stop when done
make stop
```

That's it. No Kubernetes, no cloud setup needed.

---

## Features

**LLM Gateway**
- Proxies requests to Groq, OpenAI, or Anthropic (provider abstraction)
- SSE streaming — tokens arrive word-by-word
- API key authentication
- Redis-backed rate limiting (token bucket)
- Graceful degradation — works without Redis
- SQLite persistence — conversation history stored locally
- Conversation history API (`GET /v1/chat/history`)
- System-wide CLI (`make install` then just `chat "message"`)

**Observability** (all on the Grafana dashboard)
- Request throughput (success vs error)
- Latency percentiles (p50, p95, p99)
- Token usage (prompt vs completion)
- Per-request cost estimate
- Rate-limited request tracking
- Filter by LLM model

**Ops & Deployment**
- Hardened Helm chart — HPA autoscaling, PodDisruptionBudget, resource limits, liveness/readiness probes
- Terraform module — deploy a GKE cluster + the gateway in one `apply`
- Response caching, content guardrails, and webhook notifications
- Live end-to-end test suite (`e2e/`) for real LLM calls
- MkDocs documentation site (`docs/`)

---

## Commands

```bash
make run        # Start full stack (Gateway + Redis + Prometheus + Grafana)
make stop       # Stop everything
make test       # Run tests
make lint       # Lint Python code
make build      # Build Docker image
make docs       # Build + serve the documentation site (http://localhost:8001)
make install    # Install 'chat' command system-wide ($HOME/.local/bin/chat)
make clean      # Remove containers, volumes, .venv
./chat.py "..." # Send a message via CLI
chat -s "..."   # Stream tokens as they arrive (after make install)
chat --history  # Browse past conversations
chat -c <id> "message"  # Continue a specific conversation
```

---

## Metrics

| Metric | Type | What it tracks |
|---|---|---|
| `llm_request_total` | Counter | Requests by model and status (success/error) |
| `llm_request_duration_seconds` | Histogram | Request latency (p50/p95/p99) |
| `llm_tokens_total` | Counter | Tokens used (prompt vs completion) |
| `llm_estimated_cost_dollars` | Gauge | Estimated cost per request |
| `llm_rate_limited_total` | Counter | Rate-limited requests |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Gateway | Python 3.11, FastAPI, httpx |
| Monitoring | Prometheus, Grafana, prometheus-client |
| Rate Limiting | Redis |
| LLM Providers | Groq (default), OpenAI, Anthropic |
| Persistence | SQLite |
| Container | Docker, Docker Compose |
| Orchestration | Helm, Minikube *(optional)* |
| Infrastructure | Terraform (GKE) |
| Docs | MkDocs (Material theme) |
| CI/CD | GitHub Actions, GitHub Container Registry |

---

## Project Structure

```
├── app/                        # FastAPI gateway
│   ├── main.py                 # Entrypoint
│   ├── config.py               # Settings
│   ├── database.py             # SQLite persistence layer
│   ├── providers/              # Multi-provider LLM abstraction
│   │   ├── base.py             # Abstract provider interface
│   │   ├── openai_like.py      # OpenAI-compatible (Groq, OpenAI)
│   │   ├── anthropic.py        # Anthropic client
│   │   └── router.py           # Provider selection
│   ├── routes/                 # API endpoints
│   ├── middleware/             # Auth + rate limiting
│   ├── proxy/                  # Legacy LLM client
│   └── metrics/                # Prometheus metrics
├── grafana/                    # Dashboard + provisioning
├── prometheus/                 # Prometheus scrape config
├── helm/                       # Kubernetes Helm chart (HPA, PDB, probes)
├── terraform/                  # GKE cluster + Helm deploy
├── docs/                       # MkDocs documentation site
├── tests/                      # Pytest unit suite
├── e2e/                        # Live end-to-end tests (real LLM calls)
├── ui/                         # Optional HTML chat UI
├── assets/                     # Demo GIF and MP4
├── chat.py                     # CLI client
├── mkdocs.yml                  # Docs site config
├── docker-compose.yml          # Local stack
├── Makefile                    # Common commands
├── setup.sh                    # Bootstrap script
├── Dockerfile
└── requirements.txt
```

## Deployment

### Kubernetes (Helm) — production

The chart includes HPA autoscaling, a PodDisruptionBudget, resource
requests/limits, and liveness/readiness probes out of the box.

```bash
minikube start
helm install llm-gateway ./helm/ \
  --set secrets.groqApiKey=gsk_your_key \
  --set secrets.gatewayApiKey=your-admin-key \
  --set image.repository=ghcr.io/your-username/llm-ops-gateway
kubectl port-forward svc/llm-gateway-gateway 8000:8000
kubectl port-forward svc/llm-gateway-grafana 4000:3000
```

### Cloud (Terraform / GKE)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # set project_id + secrets
terraform init && terraform apply
```

See `terraform/README.md` and the [docs site](docs) for full instructions.

### Documentation

```bash
make docs       # build + serve at http://localhost:8001
make docs-build # static site into site/
```
