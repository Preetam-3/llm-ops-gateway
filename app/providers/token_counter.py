"""Token estimation utilities (rough count, no external dependency)."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens in a message list (role + content overhead)."""
    total = 0
    for msg in messages:
        # Each message has ~4 tokens of overhead (role formatting, etc.)
        total += 4
        total += estimate_tokens(msg.get("content", ""))
        total += estimate_tokens(msg.get("role", ""))
    return total
