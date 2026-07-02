# LLM Ops Gateway — Project Status

## Quick Identity

| Field | Value |
|---|---|
| Project | llm-ops-gateway |
| Repo | github.com/Preetam-3/llm-ops-gateway |
| Purpose | Self-hosted API gateway for LLMs with observability |
| Stack | FastAPI, Redis, Prometheus, Grafana, K8s |
| LLM Provider | Groq API (free, OpenAI-compatible) |

---

## Current Status (2026-06-30)

```
Phase 1: Foundation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
Phase 2: Developer Experience ━━━━━━━━━━━━━━━━━━━━□□□□□□□□□□  50%
Phase 3: Core Features ━━━━━□□□□□□□□□□□□□□□□□□□□□□□□□□□□□□  20%
Phase 4: Production Ready ━━□□□□□□□□□□□□□□□□□□□□□□□□□□□□□□□□  10%
```

### What Works Now

- [x] FastAPI gateway with Groq API integration
- [x] API key authentication (single shared key)
- [x] Redis-backed rate limiting (token bucket)
- [x] Prometheus metrics (requests, latency, tokens, cost, rate limits)
- [x] CLI client (`./chat.py "message"`)
- [x] Chat UI (`ui/index.html`)
- [x] Dockerfile for container builds
- [x] Helm chart (Gateway + Redis + Prometheus + Grafana)
- [x] Prometheus scrape config
- [x] Grafana dashboard template (5 panels)
- [x] GitHub Actions CI (lint → test → build → push to ghcr.io)
- [x] Pytest test suite (5 tests, all passing)
- [x] Auto-venv detection in chat.py

---

## Improvement Roadmap

### Phase 2: Developer Experience (In Progress)

**Goal: Clone → one command → it works. No K8s required for dev.**

| # | Task | Status | Priority |
|---|---|---|---|
| 1 | Add `docker-compose.yml` for local dev (no Helm needed) | ⬜ TODO | 🔴 High |
| 2 | Add `Makefile` with common commands | ⬜ TODO | 🔴 High |
| 3 | Add `setup.sh` bootstrap script | ⬜ TODO | 🔴 High |
| 4 | Add `docker-compose.override.yml` for development | ⬜ TODO | 🟡 Medium |
| 5 | Add health check that works without Redis (degraded mode) | ⬜ TODO | 🟡 Medium |

### Phase 3: Core Features

**Goal: Multi-provider support, streaming, persistence, proper auth.**

| # | Task | Status | Priority |
|---|---|---|---|
| 6 | SSE streaming support (`GET /v1/chat/stream`) | ⬜ TODO | 🔴 High |
| 7 | Multi-LLM provider support (OpenAI, Groq, Anthropic) | ⬜ TODO | 🔴 High |
| 8 | SQLite database for persistence (users, keys, logs) | ⬜ TODO | 🔴 High |
| 9 | Multi-user API key management (create/revoke keys) | ⬜ TODO | 🔴 High |
| 10 | Conversation history endpoint (`GET /v1/chat/history`) | ⬜ TODO | 🟡 Medium |
| 11 | Request/response logging with search | ⬜ TODO | 🟡 Medium |
| 12 | Cumulative cost tracking (total spend, daily/monthly) | ⬜ TODO | 🟡 Medium |
| 13 | Model fallback (auto-retry with different provider) | ⬜ TODO | 🟡 Medium |
| 14 | Token usage estimates before sending | ⬜ TODO | 🟢 Low |

### Phase 4: Administration & Operations

**Goal: Admin dashboard, guardrails, production hardening.**

| # | Task | Status | Priority |
|---|---|---|---|
| 15 | Admin dashboard (React or embedded) | ⬜ TODO | 🔴 High |
| 16 | Usage analytics dashboard (per user, per key, per model) | ⬜ TODO | 🔴 High |
| 17 | IP-based rate limiting (in addition to key-based) | ⬜ TODO | 🟡 Medium |
| 18 | Response caching (identical prompts return cached) | ⬜ TODO | 🟡 Medium |
| 19 | Content guardrails (prompt/response filtering) | ⬜ TODO | 🟡 Medium |
| 20 | Webhook notifications (slack/email on thresholds) | ⬜ TODO | 🟢 Low |
| 21 | API key rotation & expiry | ⬜ TODO | 🟢 Low |

### Phase 5: Deployment & Docs

**Goal: Production-ready deployment, polished documentation.**

| # | Task | Status | Priority |
|---|---|---|---|
| 22 | Kubernetes production configs (HPA, PDB, resource limits) | ⬜ TODO | 🟡 Medium |
| 23 | Terraform/Pulumi for cloud deployment | ⬜ TODO | 🟢 Low |
| 24 | API documentation website (MkDocs or similar) | ⬜ TODO | 🟡 Medium |
| 25 | End-to-end tests with real LLM calls | ⬜ TODO | 🟡 Medium |

---

## Architecture Decisions

### Current

- **In-process metrics**: prometheus-client inside FastAPI (no sidecar)
- **Single provider**: Groq only (free, OpenAI-compatible)
- **Stateless requests**: No conversation memory
- **Single API key**: Shared across all users
- **K8s-first deployment**: Helm chart, but heavy for local dev

### Planned Changes

- Add `docker-compose.yml` as primary dev experience (K8s optional)
- Multi-provider routing layer: `LLMRouter` class dispatches by config
- SQLite for persistence (zero-dependency, file-based)
- Proper API key table with multiple keys per user
- Streaming via SSE for lower latency perception

---

## Project Structure

```
llm-ops-gateway/
├── app/                    # FastAPI gateway application
│   ├── main.py             # App entrypoint + lifespan
│   ├── config.py           # Settings from .env
│   ├── routes/
│   │   ├── chat.py         # POST /v1/chat
│   │   └── health.py       # GET /health
│   ├── middleware/
│   │   ├── auth.py         # API key validation
│   │   └── rate_limit.py   # Redis token bucket
│   ├── proxy/
│   │   └── groq_client.py  # httpx client for Groq API
│   └── metrics/
│       └── collectors.py   # Prometheus metric definitions
├── helm/                   # Kubernetes Helm chart
├── prometheus/             # Prometheus scrape config
├── grafana/                # Grafana dashboard JSON
├── tests/                  # Pytest test suite
├── ui/                     # Optional chat UI
├── chat.py                 # CLI client (auto-detects venv)
├── Dockerfile
├── docker-compose.yml      # TODO: Add for local dev
├── Makefile                # TODO: Add common commands
├── setup.sh                # TODO: Add bootstrap script
├── CLAUDE.md               # This file — project status & roadmap
└── README.md               # Project documentation
```

## Commands Reference

```bash
# Run locally (current)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
pytest -v

# Lint
ruff check app/ tests/ chat.py

# CLI chat
./chat.py "Your message"

# Full K8s stack
helm install llm-gateway ./helm/
kubectl port-forward svc/llm-gateway-gateway 8000:8000
kubectl port-forward svc/llm-gateway-grafana 4000:3000
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| GROQ_API_KEY | — | Groq API key (required) |
| GATEWAY_API_KEY | dev-key | API key for client auth |
| REDIS_URL | redis://localhost:6379 | Redis connection string |
| GROQ_MODEL | llama-3.1-8b-instant | Default LLM model |
| MAX_REQUESTS_PER_MINUTE | 30 | Rate limit per key |

## Changelog

| Date | What Changed |
|---|---|
| 2026-06-30 | Initial scaffold complete. FastAPI gateway with Groq, metrics, rate limiting, CLI, UI, Helm chart, CI. |
