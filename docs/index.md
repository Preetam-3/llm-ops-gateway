# LLM Ops Gateway

A self-hosted API gateway for LLMs with built-in observability — track
requests, latency, token usage, cost, and rate limits through a live
Grafana dashboard.

Works with any OpenAI-compatible provider (Groq, OpenAI, Anthropic) and
runs locally with one command.

## Features

- **Multi-provider** — Groq (default), OpenAI, and Anthropic behind one
  unified OpenAI-compatible API
- **SSE streaming** — `POST /v1/chat/stream` delivers tokens as they arrive
- **API key auth** — DB-backed multi-user keys with rotation & expiry
- **Rate limiting** — Redis token bucket, per-key and per-IP
- **Observability** — Prometheus metrics + Grafana dashboard (throughput,
  latency percentiles, tokens, cost, rate limits)
- **Persistence** — SQLite conversation history, request/response logs
- **Cost tracking** — daily/monthly totals and per-model, per-key splits
- **Production hardening** — caching, content guardrails, webhooks,
  model fallback, Helm + Terraform deployment

## Architecture at a glance

```
client ──► Gateway (:8000) ──► LLM provider (Groq / OpenAI / Anthropic)
                │
                ├── Redis      (rate limiting + response cache)
                ├── SQLite     (conversations, keys, logs)
                └── Prometheus (metrics scraped by Grafana)
```

See [Architecture](architecture.md) for details.

## Quick start

```bash
chmod +x setup.sh && ./setup.sh   # one-command setup
make run                          # boot Gateway + Redis + Prometheus + Grafana
./chat.py "What is Docker?"       # talk to the model
```

Full instructions in [Getting Started](getting-started.md).