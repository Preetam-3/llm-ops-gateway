# Architecture

## Overview

The gateway sits between your clients and upstream LLM providers. Every
request passes through a pipeline that adds authentication, rate limiting,
caching, guardrails, persistence, metrics, and logging — then forwards the
payload to the configured provider and normalizes the response.

```
client ──► Auth ──► Rate Limit ──► Guardrail ──► Cache? ──► Provider Router
                                            │                    └─► Groq / OpenAI / Anthropic
                                            │                    ┌──────────────────────▼
                                            └─► (miss) ──────────┘   response
                                                                │
                                            Save message ◄──────┤
                                            Log request  ◄──────┤
                                            Metrics      ◄──────┘
```

## Components

### `app/`

| Module | Responsibility |
|---|---|
| `main.py` | App entrypoint, lifespan setup, admin dashboard, `/metrics` |
| `config.py` | All settings from environment variables |
| `database.py` | SQLite layer — conversations, messages, API keys, request logs |
| `cache.py` | Redis response cache for identical requests |
| `guardrails.py` | Regex blocklist filtering for prompts and responses |
| `webhooks.py` | Slack-compatible event notifications |
| `providers/` | Multi-provider abstraction (`BaseLLMProvider`) |
| `routes/` | HTTP endpoints (chat, health, admin keys, logs) |
| `middleware/` | Auth and rate limiting |
| `metrics/` | Prometheus metric definitions |

### Provider abstraction

All providers implement `BaseLLMProvider` and normalize their responses
to an OpenAI-compatible shape:

```json
{
  "choices": [{"message": {"content": "..."}}],
  "model": "...",
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

`ProviderRouter` handles provider lifecycle and fallback — if the primary
provider fails, it retries each configured fallback in order.

### Persistence

SQLite stores:

- `conversations` and `messages` (chat history)
- `api_keys` (hashed keys, prefixes, revocation, expiry)
- `request_logs` (full request/response, tokens, cost, status)

The admin dashboard and `/v1/logs/*` endpoints read from these tables.

## Metrics

Exposed at `/metrics` in Prometheus exposition format:

| Metric | Type |
|---|---|
| `llm_request_total{model,status}` | Counter |
| `llm_request_duration_seconds{model}` | Histogram |
| `llm_tokens_total{model,type}` | Counter |
| `llm_estimated_cost_dollars{model}` | Gauge |
| `llm_rate_limited_total` | Counter |

## Degraded mode

The gateway works without Redis — if Redis is unreachable, rate limiting
and caching silently no-op and requests flow through.

## Deployment topology

See [Deployment](deployment.md) for Docker Compose, Helm, and Terraform
options.