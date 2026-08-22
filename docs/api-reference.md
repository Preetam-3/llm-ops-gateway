# API Reference

Base URL: `http://localhost:8000` (or wherever you deploy the gateway).

## Authentication

Almost every endpoint requires a bearer token:

```
Authorization: Bearer <gateway_api_key>
```

The admin key (the `GATEWAY_API_KEY` env var) can call everything.
DB-managed keys (created via `POST /v1/admin/keys`) can call the
chat endpoints but not the admin/log endpoints.

| Scope | Admin key | DB-managed key |
|---|---|---|
| `GET /health` | yes | yes |
| `POST /v1/chat`, `/v1/chat/stream`, `/v1/chat/estimate` | yes | yes |
| `GET /v1/chat/history*` | yes | yes |
| `/v1/admin/*`, `/v1/logs*`, `/admin` | yes | no |

## Health

### `GET /health`

Check service health.

```json
{"status": "ok"}
```

## Chat

### `POST /v1/chat`

Send a chat completion request.

**Request body:**

```json
{
  "messages": [{"role": "user", "content": "What is Docker?"}],
  "conversation_id": "optional-existing-id"
}
```

**Response:**

```json
{
  "conversation_id": "...",
  "reply": "Docker is a containerization platform...",
  "model": "llama-3.1-8b-instant",
  "usage": {"prompt_tokens": 12, "completion_tokens": 45, "total_tokens": 57},
  "duration_seconds": 1.234,
  "estimated_cost": 0.0000028
}
```

### `POST /v1/chat/stream`

Stream a chat completion via Server-Sent Events (SSE).

**Request body:** same as `/v1/chat`.

**Response:** `text/event-stream`. Each event is a JSON line:

```json
data: {"content": "Hello"}
data: {"content": " world"}
data: {"finish_reason": "stop"}
data: {"conversation_id": "..."}
data: [DONE]
```

### `POST /v1/chat/estimate`

Estimate the token count of a message list before sending.

**Request body:**

```json
{"messages": [{"role": "user", "content": "hello world"}]}
```

**Response:**

```json
{"estimated_tokens": 3, "messages_count": 1, "note": "Rough estimate..."}
```

### `GET /v1/chat/history`

List conversations (newest first).

| Query param | Default | Description |
|---|---|---|
| `limit` | `20` | Max 100 |
| `offset` | `0` | Pagination offset |

**Response:**

```json
{
  "conversations": [
    {"id": "...", "title": "", "created_at": "...", "updated_at": "...", "preview": "..."}
  ],
  "limit": 20,
  "offset": 0
}
```

### `GET /v1/chat/history/{conv_id}`

Fetch all messages in a conversation.

```json
{
  "conversation_id": "...",
  "messages": [{"id": "...", "role": "user", "content": "...", "model": null}]
}
```

## Admin — API keys

All `/v1/admin/*` endpoints require the admin key.

### `POST /v1/admin/keys`

Create an API key. The raw key is shown **only once**.

**Request body:**

```json
{"name": "Alice", "expires_at": "2026-12-31T23:59:59"}
```

`expires_at` is optional (ISO 8601).

**Response:**

```json
{
  "id": "...",
  "raw_key": "gw_...",
  "name": "Alice",
  "prefix": "gw_a1b2c3d4",
  "expires_at": "2026-12-31T23:59:59",
  "warning": "Save this key — it will not be shown again."
}
```

### `GET /v1/admin/keys`

List keys (prefixes only — hashes never leak).

### `DELETE /v1/admin/keys/{key_id}`

Revoke a key.

```json
{"status": "revoked"}
```

## Admin — Logs & analytics

All `/v1/logs*` endpoints require the admin key.

### `GET /v1/logs`

Search request/response logs.

| Query param | Description |
|---|---|
| `q` | Full-text search on request/response bodies |
| `model` | Filter by model name |
| `status` | `success` or `error` |
| `start_date` / `end_date` | `YYYY-MM-DD` range |
| `limit` | Max 200 (default 50) |
| `offset` | Pagination offset |

### `GET /v1/logs/stats`

Aggregate statistics:

```json
{
  "stats": {
    "total_requests": 42,
    "total_prompt_tokens": 1000,
    "total_completion_tokens": 500,
    "total_tokens": 1500,
    "total_cost": 0.003,
    "avg_duration": 1.2
  }
}
```

### `GET /v1/logs/costs/by-period?period=day`

Daily or monthly cost breakdown (`period=day|month`).

### `GET /v1/logs/costs/by-model`

Cost and usage grouped by model.

### `GET /v1/logs/costs/by-key`

Cost and usage grouped by API key.

## Admin — Dashboard & cache

### `GET /admin`

Serves the admin dashboard HTML (requires admin key).

### `POST /admin/cache/clear`

Clear all cached LLM responses.

```json
{"status": "ok", "cleared": 12, "note": "Cached LLM responses cleared"}
```

## Observability

### `GET /metrics`

Prometheus metrics in exposition format (no auth). See
[Architecture](architecture.md#metrics) for the metric list.

## Error codes

| Code | Meaning |
|---|---|
| `401` | Missing or invalid Authorization header |
| `403` | Bad/revoked/expired key, or admin-only endpoint |
| `404` | Resource not found |
| `429` | Rate limit exceeded (key or IP) |
| `400` | Guardrail blocked, empty messages, or bad input |
| `502` | All LLM providers failed upstream |