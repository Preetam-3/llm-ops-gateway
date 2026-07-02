#!/usr/bin/env python3
"""CLI client for the LLM Ops Gateway.

Usage:
    ./chat.py "Your message here"
    python chat.py "Your message here"

Requires a .env file with:
    GATEWAY_API_KEY=your_key
    GATEWAY_URL=http://localhost:8000
"""

import os
import sys

# Auto-detect virtual environment
_venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python")
if _venv != sys.executable and os.path.exists(_venv):
    os.execv(_venv, [_venv] + sys.argv)

# ruff: noqa: E402
import httpx
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_KEY = os.getenv("GATEWAY_API_KEY", "")


def chat(message: str) -> None:
    payload = {"messages": [{"role": "user", "content": message}]}
    headers = {"Authorization": f"Bearer {API_KEY}"}

    with httpx.Client(base_url=GATEWAY_URL) as client:
        resp = client.post("/v1/chat", json=payload, headers=headers)

    if resp.status_code == 401:
        print("Error: Missing or invalid API key.")
        sys.exit(1)
    elif resp.status_code == 403:
        print("Error: Invalid API key.")
        sys.exit(1)
    elif resp.status_code == 429:
        print("Error: Rate limit exceeded. Try again later.")
        sys.exit(1)
    elif resp.status_code != 200:
        print(f"Error: Gateway returned HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    print(f"\n{data['reply']}")
    print(f"\n--- Model: {data['model']} | Tokens: {data['usage']['total_tokens']} "
          f"| Cost: ${data['estimated_cost']} | Latency: {data['duration_seconds']}s ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chat.py \"Your message here\"")
        sys.exit(1)
    chat(" ".join(sys.argv[1:]))
