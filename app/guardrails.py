"""Content guardrails — prompt and response filtering."""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Default blocked patterns (configurable via blocklist file)
_DEFAULT_BLOCKED_PATTERNS: list[str] = [
    # Add default patterns here if needed
]

_blocked_patterns: list[re.Pattern] = []
_check_prompts: bool = True
_check_responses: bool = True


def init_guardrails(
    blocklist_path: str | None = None,
    check_prompts: bool = True,
    check_responses: bool = True,
) -> None:
    """Load blocklist patterns from file or use defaults."""
    global _blocked_patterns, _check_prompts, _check_responses
    _check_prompts = check_prompts
    _check_responses = check_responses

    patterns = list(_DEFAULT_BLOCKED_PATTERNS)

    if blocklist_path:
        path = Path(blocklist_path)
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8").strip()
                if raw:
                    custom = json.loads(raw)
                    if isinstance(custom, list):
                        patterns.extend(custom)
                    logger.info("Loaded %d patterns from %s", len(custom), blocklist_path)
            except Exception as e:
                logger.warning("Failed to load blocklist %s: %s", blocklist_path, e)

    _blocked_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    logger.info("Guardrails initialized with %d patterns", len(_blocked_patterns))


def _check_text(text: str, context: str = "content") -> str | None:
    """Check text against blocked patterns. Returns reason if blocked, None if OK."""
    if not _blocked_patterns:
        return None
    for pattern in _blocked_patterns:
        match = pattern.search(text)
        if match:
            reason = f"Blocked by pattern '{pattern.pattern}' in {context}"
            logger.warning("Guardrail blocked %s: matched '%s'", context, match.group())
            return reason
    return None


def check_prompt(messages: list[dict]) -> str | None:
    """Check user messages against blocklist. Returns reason if blocked."""
    if not _check_prompts:
        return None
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            reason = _check_text(content, context="prompt")
            if reason:
                return reason
    return None


def check_response(text: str) -> str | None:
    """Check assistant response against blocklist. Returns reason if blocked."""
    if not _check_responses:
        return None
    return _check_text(text, context="response")
