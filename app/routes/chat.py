import time
from fastapi import APIRouter, Depends, HTTPException, Request
from app.metrics.collectors import (
    llm_request_total,
    llm_request_duration_seconds,
    llm_tokens_total,
    llm_estimated_cost_dollars,
)
from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import rate_limiter
from app.proxy.groq_client import groq_client

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(rate_limiter.check)])


@router.post("/v1/chat")
async def chat_completion(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    if not messages:
        raise HTTPException(status_code=400, detail="messages field is required")

    start = time.monotonic()

    try:
        groq_response = await groq_client.chat_completion(messages)
    except Exception as e:
        llm_request_total.labels(model=groq_client.model, status="error").inc()
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    duration = time.monotonic() - start

    usage = groq_response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Metrics
    llm_request_total.labels(model=groq_client.model, status="success").inc()
    llm_request_duration_seconds.labels(model=groq_client.model).observe(duration)
    llm_tokens_total.labels(model=groq_client.model, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=groq_client.model, type="completion").inc(completion_tokens)

    # Rough cost estimate: Llama 3 8B ~$0.05 per 1M tokens
    estimated_cost = (total_tokens / 1_000_000) * 0.05
    llm_estimated_cost_dollars.labels(model=groq_client.model).set(estimated_cost)

    return {
        "reply": groq_response["choices"][0]["message"]["content"],
        "model": groq_response.get("model", groq_client.model),
        "usage": usage,
        "duration_seconds": round(duration, 3),
        "estimated_cost": round(estimated_cost, 8),
    }
