# Getting Started

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- A free [Groq API key](https://console.groq.com)

## One-command setup

```bash
chmod +x setup.sh && ./setup.sh
```

The setup script:

1. Checks prerequisites (Docker, Python)
2. Creates `.env` from `.env.example` and prompts for your Groq API key
3. Creates a Python virtual environment and installs dependencies

## Running the stack

```bash
make run
```

This boots:

| Service | Address | Notes |
|---|---|---|
| Gateway | `http://localhost:8000` | FastAPI app |
| Grafana | `http://localhost:4000` | login `admin` / `admin` |
| Prometheus | `http://localhost:9091` | scrapes the gateway |
| Redis | `localhost:6379` | rate limiting + cache |

## Talking to the model

```bash
./chat.py "What is Docker?"
./chat.py -s "stream this response"     # streaming
./chat.py --history                     # browse past conversations
./chat.py -c <id> "continue this chat"  # continue a conversation
```

## Running without Docker

For quick local development (no Redis/Prometheus/Grafana — degraded mode):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing & linting

```bash
make test      # pytest
make lint      # ruff check
```

## Next steps

- Configure the gateway via [Configuration](configuration.md)
- Deploy to production via [Deployment](deployment.md)
- Call the gateway programmatically via [API Reference](api-reference.md)