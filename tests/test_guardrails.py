"""Tests for content guardrails."""
import json

from app.guardrails import check_prompt, check_response, init_guardrails


def _reset_guardrails():
    """Reset to no patterns for clean test state."""
    init_guardrails(blocklist_path=None, check_prompts=True, check_responses=True)


def test_guardrails_disabled():
    """When disabled, no content should be blocked."""
    init_guardrails(blocklist_path=None, check_prompts=False, check_responses=False)
    assert check_prompt([{"role": "user", "content": "anything"}]) is None
    assert check_response("anything") is None


def test_guardrails_block_prompt(tmp_path):
    """Prompt matching blocked pattern should be rejected."""
    blocklist = tmp_path / "blocklist.json"
    blocklist.write_text(json.dumps(["evil", "badword"]))
    init_guardrails(blocklist_path=str(blocklist), check_prompts=True, check_responses=False)

    result = check_prompt([{"role": "user", "content": "this is evil content"}])
    assert result is not None
    assert "Blocked" in result

    # Non-blocked content should pass
    assert check_prompt([{"role": "user", "content": "good content"}]) is None


def test_guardrails_block_response(tmp_path):
    """Response matching blocked pattern should be rejected."""
    blocklist = tmp_path / "blocklist.json"
    blocklist.write_text(json.dumps(["harmful"]))
    init_guardrails(blocklist_path=str(blocklist), check_prompts=False, check_responses=True)

    result = check_response("this contains harmful material")
    assert result is not None
    assert "Blocked" in result

    assert check_response("safe response") is None


def test_guardrails_empty_patterns():
    """No patterns means nothing is blocked."""
    _reset_guardrails()
    assert check_prompt([{"role": "user", "content": "anything"}]) is None
    assert check_response("anything") is None


def test_guardrails_case_insensitive(tmp_path):
    """Pattern matching should be case insensitive."""
    blocklist = tmp_path / "blocklist.json"
    blocklist.write_text(json.dumps(["secret"]))
    init_guardrails(blocklist_path=str(blocklist), check_prompts=True, check_responses=False)

    assert check_prompt([{"role": "user", "content": "This is SECRET"}]) is not None
    assert check_prompt([{"role": "user", "content": "this is Secret"}]) is not None
