#!/usr/bin/env python3
"""CLI client for the LLM Ops Gateway.

Usage:
    chat "Your message here"             # Non-streaming (full response at once)
    chat -s "Your message here"          # Streaming (tokens appear as they arrive)
    chat --history                       # Browse conversation history
    chat -c <id> "Your message here"     # Continue a conversation

Requires a .env file in the project directory with:
    GATEWAY_API_KEY=your_key
    GATEWAY_URL=http://localhost:8000
"""

import json
import os
import sys

# Auto-detect virtual environment
_script_dir = os.path.dirname(os.path.realpath(__file__))
_venv = os.path.join(_script_dir, ".venv", "bin", "python")
if _venv != sys.executable and os.path.exists(_venv):
    os.execv(_venv, [_venv] + sys.argv)

# ruff: noqa: E402
import httpx
from dotenv import load_dotenv

# Load .env from script directory so it works when symlinked into $PATH
load_dotenv(dotenv_path=os.path.join(_script_dir, ".env"))

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_KEY = os.getenv("GATEWAY_API_KEY", "")


# ── Core API helpers ──


def _post(path: str, payload: dict) -> httpx.Response:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with httpx.Client(base_url=GATEWAY_URL, timeout=120.0) as client:
        resp = client.post(path, json=payload, headers=headers)
    _check_status(resp)
    return resp


def _get(path: str) -> httpx.Response:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with httpx.Client(base_url=GATEWAY_URL, timeout=30.0) as client:
        resp = client.get(path, headers=headers)
    _check_status(resp)
    return resp


def _check_status(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        print("Error: Missing or invalid API key.", file=sys.stderr)
        sys.exit(1)
    elif resp.status_code == 403:
        print("Error: Invalid API key.", file=sys.stderr)
        sys.exit(1)
    elif resp.status_code == 429:
        print("Error: Rate limit exceeded. Try again later.", file=sys.stderr)
        sys.exit(1)
    elif resp.status_code != 200:
        print(f"Error: Gateway returned HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)


# ── One-shot chat (existing behavior) ──


def chat(message: str, conv_id: str | None = None) -> None:
    """Non-streaming — sends message, prints full response."""
    payload = {"messages": [{"role": "user", "content": message}]}
    if conv_id:
        payload["conversation_id"] = conv_id

    data = _post("/v1/chat", payload).json()
    print(f"\n{data['reply']}")
    print(f"\n--- Model: {data['model']} | Tokens: {data['usage']['total_tokens']} "
          f"| Cost: ${data['estimated_cost']} | Latency: {data['duration_seconds']}s ---")


def chat_stream(message: str, conv_id: str | None = None) -> None:
    """Streaming — tokens print as they arrive."""
    payload = {"messages": [{"role": "user", "content": message}]}
    if conv_id:
        payload["conversation_id"] = conv_id

    headers = {"Authorization": f"Bearer {API_KEY}"}
    with httpx.Client(base_url=GATEWAY_URL, timeout=300.0) as client:
        with client.stream("POST", "/v1/chat/stream", json=payload, headers=headers) as resp:
            _check_status(resp)
            print()
            for line in resp.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if "content" in event:
                    print(event["content"], end="", flush=True)
                if "finish_reason" in event:
                    print()
                if "error" in event:
                    print(f"\nError: {event['error']}", file=sys.stderr)


# ── History + interactive mode ──


def show_history() -> None:
    """Fetch conversation history, display it nicely, and let user pick one."""
    data = _get("/v1/chat/history").json()
    conversations = data.get("conversations", [])

    if not conversations:
        print("\n  No conversations yet.")
        return

    print("\n  \033[1mConversations:\033[0m")
    print("  \u2500" * 72)
    for i, conv in enumerate(conversations, 1):
        preview = (conv.get("preview") or "(empty)")[:55]
        updated = (conv.get("updated_at") or "")[:16]
        print(f"  {i:>2} \u2502 {preview:<55} {updated}")
    print("  \u2500" * 72)

    choice = input("\n  Select conversation (\033[1mQ\033[0m to quit): ").strip()
    if choice.lower() in ("q", ""):
        return

    try:
        idx = int(choice) - 1
        conv = conversations[idx]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return

    _interactive_chat(conv["id"])


def _interactive_chat(conv_id: str) -> None:
    """Interactive chat loop within an existing conversation."""
    print(f"\n  Continuing conversation \033[2m{conv_id[:16]}...\033[0m")
    print("  (\033[3m/q\033[0m to quit, \033[3mCtrl+C\033[0m to exit)")
    try:
        while True:
            msg = input("\n  \033[1mYou:\033[0m ").strip()
            if not msg:
                continue
            if msg == "/q":
                break
            chat_stream(msg, conv_id=conv_id)
    except (EOFError, KeyboardInterrupt):
        print()


def _print_usage() -> None:
    print(__doc__, end="")


# ── Entry point ──

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        _print_usage()
        sys.exit(1)

    match args[0]:
        case "-s" | "--stream":
            if len(args) < 2:
                print("Usage: chat -s \"Your message here\"")
                sys.exit(1)
            chat_stream(" ".join(args[1:]))

        case "-c" | "--continue":
            if len(args) < 3:
                print("Usage: chat -c <conversation_id> \"Your message here\"")
                sys.exit(1)
            chat_stream(" ".join(args[2:]), conv_id=args[1])

        case "-l" | "--history":
            show_history()

        case "-h" | "--help":
            _print_usage()

        case _:
            chat(" ".join(args))
