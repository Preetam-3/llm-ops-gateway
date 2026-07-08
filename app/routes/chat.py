import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.cache import cache_get, cache_set
from app.database import (
    get_conversations,
    get_messages,
    log_request,
    save_conversation,
    save_message,
)
from app.providers.token_counter import estimate_messages_tokens
from app.metrics.collectors import (
    llm_request_total,
    llm_request_duration_seconds,
    llm_tokens_total,
    llm_estimated_cost_dollars,
)
from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import rate_limiter
from app.providers.router import provider_router

router = APIRouter(dependencies=[Depends(verify_api_key), Depends(rate_limiter.check)])


@router.post("/v1/chat")
async def chat_completion(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    conv_id = body.get("conversation_id") or str(uuid.uuid4())

    if not messages:
        raise HTTPException(status_code=400, detail="messages field is required")

    # Save user messages to DB
    await save_conversation(conv_id)
    user_content = " ".join(m["content"] for m in messages if m.get("role") == "user")
    await save_message(conv_id, "user", user_content or messages[-1]["content"])

    start = time.monotonic()

    # Check cache
    model_name = provider_router.get_provider().model
    cached = await cache_get(model_name, messages)
    if cached:
        llm_response = cached
        cached_hit = True
    else:
        cached_hit = False
        try:
            llm_response = await provider_router.chat_with_fallback(messages)
        except Exception as e:
            llm_request_total.labels(model="unknown", status="error").inc()
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    # Store in cache on success
    if not cached_hit:
        await cache_set(model_name, messages, llm_response)

    duration = time.monotonic() - start

    usage = llm_response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Rough cost estimate: Llama 3 8B ~$0.05 per 1M tokens
    estimated_cost = (total_tokens / 1_000_000) * 0.05

    # Save assistant response to DB
    reply = llm_response["choices"][0]["message"]["content"]
    model_used = llm_response.get("model", "unknown")
    await save_message(
        conv_id, "assistant", reply,
        model=model_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        duration_seconds=duration,
    )

    # Metrics
    llm_request_total.labels(model=model_used, status="success").inc()
    llm_request_duration_seconds.labels(model=model_used).observe(duration)
    llm_tokens_total.labels(model=model_used, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=model_used, type="completion").inc(completion_tokens)
    llm_estimated_cost_dollars.labels(model=model_used).set(estimated_cost)

    # Log request/response
    auth = request.headers.get("Authorization", "")
    key_prefix = auth[7:17] if auth.startswith("Bearer ") else None
    await log_request(
        conversation_id=conv_id,
        request_body=json.dumps({"messages": messages}),
        response_body=json.dumps({"reply": reply, "model": model_used, "usage": usage}),
        model=model_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        duration_seconds=duration,
        ip_address=request.client.host if request.client else None,
        api_key_prefix=key_prefix,
    )

    return {
        "conversation_id": conv_id,
        "reply": reply,
        "model": model_used,
        "usage": usage,
        "duration_seconds": round(duration, 3),
        "estimated_cost": round(estimated_cost, 8),
    }


@router.post("/v1/chat/stream")
async def chat_completion_stream(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    conv_id = body.get("conversation_id") or str(uuid.uuid4())

    if not messages:
        raise HTTPException(status_code=400, detail="messages field is required")

    # Save user message before streaming
    await save_conversation(conv_id)
    user_content = " ".join(m["content"] for m in messages if m.get("role") == "user")
    await save_message(conv_id, "user", user_content or messages[-1]["content"])

    async def event_generator():
        start = time.monotonic()
        full_content = ""
        model_used = provider_router.get_provider().model
        try:
            async for chunk in provider_router.get_provider().chat_completion_stream(messages):
                choice = chunk.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                content = delta.get("content")

                if content:
                    full_content += content
                    yield f"data: {json.dumps({'content': content})}\n\n"

                finish_reason = choice.get("finish_reason")
                if finish_reason:
                    yield f"data: {json.dumps({'finish_reason': finish_reason})}\n\n"

            duration = time.monotonic() - start

            # Save assistant response after stream ends
            await save_message(
                conv_id, "assistant", full_content,
                model=model_used,
                duration_seconds=duration,
            )

            # Metrics
            llm_request_total.labels(model=model_used, status="success").inc()
            llm_request_duration_seconds.labels(model=model_used).observe(duration)

            # Log request/response (non-blocking after stream done)
            await log_request(
                conversation_id=conv_id,
                request_body=json.dumps({"messages": messages}),
                response_body=json.dumps({"reply": full_content, "model": model_used}),
                model=model_used,
                duration_seconds=duration,
                status="success",
            )

        except Exception as e:
            llm_request_total.labels(model=model_used, status="error").inc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            # Log the error
            await log_request(
                conversation_id=conv_id,
                request_body=json.dumps({"messages": messages}),
                response_body=json.dumps({"error": str(e)}),
                model=model_used,
                duration_seconds=time.monotonic() - start,
                status="error",
            )
        finally:
            yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/v1/chat/history")
async def chat_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conversations = await get_conversations(limit=limit, offset=offset)
    return {"conversations": conversations, "limit": limit, "offset": offset}


@router.post("/v1/chat/estimate")
async def estimate_tokens_endpoint(request: Request):
    """Estimate token count for a list of messages before sending."""
    body = await request.json()
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages field is required")
    estimated = estimate_messages_tokens(messages)
    return {
        "estimated_tokens": estimated,
        "messages_count": len(messages),
        "note": "Rough estimate based on character count. Actual tokens may vary.",
    }


@router.get("/v1/chat/history/{conv_id}")
async def chat_conversation(conv_id: str):
    messages = await get_messages(conv_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conv_id, "messages": messages}
