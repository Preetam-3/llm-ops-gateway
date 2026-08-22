# Configuration

All configuration is handled through environment variables, loaded from
`.env` at startup. See `.env.example` for the template.

## Provider selection

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Primary provider: `groq`, `openai`, or `anthropic` |
| `LLM_MODEL` | *(empty)* | Overrides the per-provider model if set |
| `PROVIDER_FALLBACK` | *(empty)* | Comma-separated fallback list, e.g. `groq,openai` |

### Groq

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required** Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Default Groq model |

### OpenAI

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | Default OpenAI model |

### Anthropic

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Default Anthropic model |

## Gateway behavior

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-key` | Admin/client key — used to authenticate and to call admin endpoints |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `MAX_REQUESTS_PER_MINUTE` | `30` | Per-key rate limit |
| `MAX_REQUESTS_PER_MINUTE_PER_IP` | `60` | Per-IP rate limit |
| `DATABASE_PATH` | `gateway.db` | SQLite file location |

## Caching

| Variable | Default | Description |
|---|---|---|
| `CACHE_ENABLED` | `true` | Enable Redis response caching |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL for identical requests |

## Guardrails

| Variable | Default | Description |
|---|---|---|
| `GUARDRAILS_ENABLED` | `false` | Enable prompt/response filtering |
| `GUARDRAILS_BLOCKLIST_PATH` | *(empty)* | Path to a JSON list of blocked regex patterns |

Example blocklist file:

```json
["evil", "badword", "harmful"]
```

## Webhooks

| Variable | Default | Description |
|---|---|---|
| `WEBHOOK_URL` | *(empty)* | Slack-compatible webhook URL for gateway events |

## Examples

```bash
# Use OpenAI with fallback to Groq
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
PROVIDER_FALLBACK=groq

# Enable guardrails with a custom blocklist
GUARDRAILS_ENABLED=true
GUARDRAILS_BLOCKLIST_PATH=./blocklist.json

# Notify a Slack channel on events
WEBHOOK_URL=https://hooks.slack.com/services/T000/B000/XXXX
```