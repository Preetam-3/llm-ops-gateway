"""Tests for the token estimation utility."""
from app.providers.token_counter import estimate_messages_tokens, estimate_tokens


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_short():
    assert estimate_tokens("hello") >= 1


def test_estimate_tokens_long():
    text = "hello world " * 100
    assert estimate_tokens(text) >= 1


def test_estimate_messages_tokens():
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    count = estimate_messages_tokens(messages)
    assert count >= estimate_tokens("hello") + estimate_tokens("hi there")
