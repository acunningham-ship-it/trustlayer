"""OpenAI-compatible proxy router for TrustLayer.

Users set OPENAI_BASE_URL=http://localhost:8000/v1 and all their AI tools
automatically flow through TrustLayer for logging, cost tracking, and routing.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from ..config import OLLAMA_BASE_URL
from ..database import AsyncSessionLocal, ProxyLog
from ..providers.openai_compat import PRICING, PROVIDER_ENDPOINTS
from ..providers.registry import get_registry
from ..routing.engine import RoutingEngine
from ..routing.rules import load_rules

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def determine_provider(model: str) -> str:
    """Determine which provider to route to based on model name."""
    m = model.lower()
    if m.startswith("claude-") or m.startswith("anthropic/"):
        return "anthropic"
    if m.startswith("gpt-") or m.startswith("openai/"):
        return "openai"
    if m.startswith("gemini-") or m.startswith("google/"):
        return "google"
    return "ollama"


def strip_provider_prefix(model: str) -> str:
    """Remove provider/ prefix if present."""
    for prefix in ("anthropic/", "openai/", "google/", "ollama/"):
        if model.lower().startswith(prefix):
            return model[len(prefix):]
    return model


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return max(1, len(text) // 4)


def calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING.get(model, (0, 0))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


async def log_request(
    source_ip: str,
    user_agent: str,
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_ms: int,
    status_code: int = 200,
    error: Optional[str] = None,
    streamed: bool = False,
    routed_from: Optional[str] = None,
    savings_usd: float = 0.0,
):
    """Non-blocking database log write."""
    try:
        async with AsyncSessionLocal() as session:
            entry = ProxyLog(
                id=str(uuid.uuid4()),
                source_ip=source_ip,
                user_agent=user_agent,
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status_code=status_code,
                error=error,
                streamed=streamed,
                routed_from=routed_from,
                savings_usd=savings_usd,
            )
            session.add(entry)
            await session.commit()
    except Exception:
        logger.exception("Failed to log proxy request")


# ---------------------------------------------------------------------------
# GET /v1/models
# ---------------------------------------------------------------------------

@router.get("/v1/models")
async def list_models():
    """Aggregate models from all configured providers in OpenAI format."""
    try:
        registry = get_registry()
        data = []

        for provider_name, provider in registry.items():
            try:
                if await provider.is_available():
                    models = await provider.list_models()
                    for m in models:
                        data.append({
                            "id": m,
                            "object": "model",
                            "created": 0,
                            "owned_by": provider_name,
                        })
            except Exception:
                logger.exception("Failed to list models for %s", provider_name)

        return {"object": "list", "data": data}
    except Exception:
        logger.exception("Failed to list models")
        return {"object": "list", "data": []}


# ---------------------------------------------------------------------------
# POST /v1/chat/completions  (the main endpoint)
# ---------------------------------------------------------------------------

@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions proxy."""
    start_time = time.time()
    source_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={
            "error": {"message": "Invalid JSON body", "type": "invalid_request_error"}
        })

    model = body.get("model", "")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature")
    max_tokens = body.get("max_tokens")

    if not model:
        return JSONResponse(status_code=400, content={
            "error": {"message": "model is required", "type": "invalid_request_error"}
        })

    # ----- SMART ROUTING -----
    routing_decision = None
    original_model = model
    try:
        rules = await load_rules()
        engine = RoutingEngine(rules=rules)
        routing_decision = await engine.evaluate(model, messages)
        if routing_decision.was_routed:
            logger.info(
                "Routing: %s -> %s (%s)",
                routing_decision.original_model,
                routing_decision.routed_model,
                routing_decision.reason,
            )
            model = routing_decision.routed_model
            body["model"] = model
    except Exception:
        logger.exception("Routing engine error, using original model")

    provider_name = determine_provider(model)
    clean_model = strip_provider_prefix(model)

    # Build extra headers for routing info
    routing_headers = {}
    if routing_decision:
        routing_headers["X-TrustLayer-Routed"] = str(routing_decision.was_routed).lower()
        routing_headers["X-TrustLayer-Original-Model"] = routing_decision.original_model
        routing_headers["X-TrustLayer-Task-Type"] = routing_decision.task_type
        if routing_decision.was_routed:
            routing_headers["X-TrustLayer-Savings"] = str(routing_decision.estimated_savings_pct) + "%"

    routed_from = original_model if routing_decision and routing_decision.was_routed else None
    savings_usd = routing_decision.estimated_savings_usd if routing_decision and routing_decision.was_routed else 0.0

    # ----- OLLAMA -----
    if provider_name == "ollama":
        response = await _proxy_ollama_chat(
            clean_model, messages, stream, temperature, max_tokens,
            source_ip, user_agent, start_time,
            routed_from=routed_from, savings_usd=savings_usd,
        )
        if isinstance(response, dict):
            return JSONResponse(content=response, headers=routing_headers)
        if isinstance(response, StreamingResponse):
            for k, v in routing_headers.items():
                response.headers[k] = v
            return response
        return response

    # ----- CLOUD PROVIDERS (OpenAI-compatible) -----
    response = await _proxy_cloud_chat(
        provider_name, clean_model, body, stream,
        source_ip, user_agent, start_time,
        routed_from=routed_from, savings_usd=savings_usd,
    )
    if isinstance(response, dict):
        return JSONResponse(content=response, headers=routing_headers)
    if isinstance(response, JSONResponse):
        for k, v in routing_headers.items():
            response.headers[k] = v
        return response
    if isinstance(response, StreamingResponse):
        for k, v in routing_headers.items():
            response.headers[k] = v
        return response
    return response


async def _proxy_ollama_chat(
    model, messages, stream, temperature, max_tokens,
    source_ip, user_agent, start_time,
    routed_from=None, savings_usd=0.0,
):
    """Forward chat to Ollama, translating OpenAI format <-> Ollama format."""
    ollama_url = OLLAMA_BASE_URL
    ollama_payload = {
        "model": model,
        "messages": messages,
        "stream": bool(stream),
    }
    if temperature is not None:
        ollama_payload.setdefault("options", {})["temperature"] = temperature
    if max_tokens is not None:
        ollama_payload.setdefault("options", {})["num_predict"] = max_tokens

    if stream:
        return StreamingResponse(
            _stream_ollama(ollama_url, ollama_payload, model, source_ip, user_agent, start_time),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{ollama_url}/api/chat", json=ollama_payload)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        asyncio.create_task(log_request(
            source_ip, user_agent, model, "ollama", 0, 0, 0.0,
            latency, 502, str(e),
        ))
        return JSONResponse(status_code=502, content={
            "error": {"message": "Ollama error: " + str(e), "type": "upstream_error"}
        })

    content = data.get("message", {}).get("content", "")
    prompt_tokens = data.get("prompt_eval_count", 0) or estimate_tokens(
        " ".join(m.get("content", "") for m in messages)
    )
    completion_tokens = data.get("eval_count", 0) or estimate_tokens(content)
    latency = int((time.time() - start_time) * 1000)

    response = _openai_chat_response(model, content, prompt_tokens, completion_tokens)

    asyncio.create_task(log_request(
        source_ip, user_agent, model, "ollama",
        prompt_tokens, completion_tokens, 0.0, latency,
        routed_from=routed_from, savings_usd=savings_usd,
    ))

    return response


async def _stream_ollama(ollama_url, payload, model, source_ip, user_agent, start_time):
    """Stream Ollama response, translating to OpenAI SSE format."""
    completion_id = "chatcmpl-" + uuid.uuid4().hex[:12]
    full_content = ""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{ollama_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_content += token
                        sse_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }],
                        }
                        yield "data: " + json.dumps(sse_chunk) + "\n\n"

                    if chunk.get("done"):
                        prompt_tokens = chunk.get("prompt_eval_count", 0)
                        completion_tokens = chunk.get("eval_count", 0)
                        final_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }],
                        }
                        yield "data: " + json.dumps(final_chunk) + "\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception("Ollama streaming error")
        error_msg = {"error": str(e)}
        yield "data: " + json.dumps(error_msg) + "\n\n"
        yield "data: [DONE]\n\n"

    # Log after stream completes
    latency = int((time.time() - start_time) * 1000)
    try:
        asyncio.create_task(log_request(
            source_ip, user_agent, model, "ollama",
            prompt_tokens, completion_tokens, 0.0, latency,
            streamed=True,
        ))
    except Exception:
        pass


async def _proxy_cloud_chat(
    provider_name, model, body, stream,
    source_ip, user_agent, start_time,
    routed_from=None, savings_usd=0.0,
):
    """Forward to a cloud provider using OpenAI-compatible API."""
    registry = get_registry()
    provider = registry.get(provider_name)

    if not provider or not await provider.is_available():
        return JSONResponse(status_code=400, content={
            "error": {
                "message": "Provider '" + provider_name + "' is not configured. Set the API key.",
                "type": "invalid_request_error",
            }
        })

    # For Anthropic, use the native Messages API
    if provider_name == "anthropic":
        return await _proxy_anthropic_chat(provider, model, body, stream, source_ip, user_agent, start_time)

    # For OpenAI and Google (OpenAI-compatible), pass through
    headers = {
        "Authorization": "Bearer " + provider.api_key,
        "Content-Type": "application/json",
    }

    forward_body = dict(body)
    forward_body["model"] = model

    target_url = provider.base_url + "/chat/completions"

    if stream:
        return StreamingResponse(
            _stream_cloud(target_url, headers, forward_body, model, provider_name, source_ip, user_agent, start_time),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(target_url, json=forward_body, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        asyncio.create_task(log_request(
            source_ip, user_agent, model, provider_name, 0, 0, 0.0,
            latency, 502, str(e),
        ))
        return JSONResponse(status_code=502, content={
            "error": {"message": "Upstream error: " + str(e), "type": "upstream_error"}
        })

    # Extract usage
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    latency = int((time.time() - start_time) * 1000)
    cost = calc_cost(model, prompt_tokens, completion_tokens)

    asyncio.create_task(log_request(
        source_ip, user_agent, model, provider_name,
        prompt_tokens, completion_tokens, cost, latency,
    ))

    return data


async def _proxy_anthropic_chat(provider, model, body, stream, source_ip, user_agent, start_time):
    """Translate OpenAI chat format to Anthropic Messages API and back."""
    messages = body.get("messages", [])

    # Extract system message if present
    system_text = ""
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_text += m.get("content", "") + "\n"
        else:
            chat_messages.append({"role": m["role"], "content": m.get("content", "")})

    anthropic_body = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": body.get("max_tokens", 4096),
    }
    if system_text.strip():
        anthropic_body["system"] = system_text.strip()
    if body.get("temperature") is not None:
        anthropic_body["temperature"] = body["temperature"]
    if stream:
        anthropic_body["stream"] = True

    headers = {
        "x-api-key": provider.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    target_url = "https://api.anthropic.com/v1/messages"

    if stream:
        return StreamingResponse(
            _stream_anthropic(target_url, headers, anthropic_body, model, source_ip, user_agent, start_time),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(target_url, json=anthropic_body, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        asyncio.create_task(log_request(
            source_ip, user_agent, model, "anthropic", 0, 0, 0.0,
            latency, 502, str(e),
        ))
        return JSONResponse(status_code=502, content={
            "error": {"message": "Anthropic error: " + str(e), "type": "upstream_error"}
        })

    content = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            content += block.get("text", "")

    prompt_tokens = data.get("usage", {}).get("input_tokens", 0)
    completion_tokens = data.get("usage", {}).get("output_tokens", 0)
    latency = int((time.time() - start_time) * 1000)
    cost = calc_cost(model, prompt_tokens, completion_tokens)

    response = _openai_chat_response(model, content, prompt_tokens, completion_tokens)

    asyncio.create_task(log_request(
        source_ip, user_agent, model, "anthropic",
        prompt_tokens, completion_tokens, cost, latency,
    ))

    return response


async def _stream_anthropic(url, headers, body, model, source_ip, user_agent, start_time):
    """Stream Anthropic SSE and translate to OpenAI SSE format."""
    completion_id = "chatcmpl-" + uuid.uuid4().hex[:12]
    full_content = ""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    etype = event.get("type", "")

                    if etype == "content_block_delta":
                        delta = event.get("delta", {})
                        token = delta.get("text", "")
                        if token:
                            full_content += token
                            sse_chunk = {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": token},
                                    "finish_reason": None,
                                }],
                            }
                            yield "data: " + json.dumps(sse_chunk) + "\n\n"

                    elif etype == "message_delta":
                        usage = event.get("usage", {})
                        completion_tokens = usage.get("output_tokens", completion_tokens)

                    elif etype == "message_start":
                        msg = event.get("message", {})
                        usage = msg.get("usage", {})
                        prompt_tokens = usage.get("input_tokens", 0)

        # Final chunk
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        }
        yield "data: " + json.dumps(final_chunk) + "\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception("Anthropic streaming error")
        yield "data: " + json.dumps({"error": str(e)}) + "\n\n"
        yield "data: [DONE]\n\n"

    latency = int((time.time() - start_time) * 1000)
    cost = calc_cost(model, prompt_tokens, completion_tokens)
    try:
        asyncio.create_task(log_request(
            source_ip, user_agent, model, "anthropic",
            prompt_tokens, completion_tokens, cost, latency,
            streamed=True,
        ))
    except Exception:
        pass


async def _stream_cloud(url, headers, body, model, provider_name, source_ip, user_agent, start_time):
    """Pass through SSE stream from OpenAI-compatible provider, accumulating tokens for logging."""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        body["stream"] = True
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        yield line + "\n\n"
                        # Try to extract usage from stream chunks
                        if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                usage = chunk.get("usage", {})
                                if usage:
                                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                    completion_tokens = usage.get("completion_tokens", completion_tokens)
                            except (json.JSONDecodeError, KeyError):
                                pass
    except Exception as e:
        logger.exception("Cloud streaming error")
        yield "data: " + json.dumps({"error": str(e)}) + "\n\n"
        yield "data: [DONE]\n\n"

    latency = int((time.time() - start_time) * 1000)
    cost = calc_cost(model, prompt_tokens, completion_tokens)
    try:
        asyncio.create_task(log_request(
            source_ip, user_agent, model, provider_name,
            prompt_tokens, completion_tokens, cost, latency,
            streamed=True,
        ))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# POST /v1/completions  (legacy)
# ---------------------------------------------------------------------------

@router.post("/v1/completions")
async def completions(request: Request):
    """Legacy completions endpoint -- translates to chat format internally."""
    start_time = time.time()
    source_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={
            "error": {"message": "Invalid JSON body", "type": "invalid_request_error"}
        })

    model = body.get("model", "")
    prompt = body.get("prompt", "")
    max_tokens = body.get("max_tokens")

    if not model:
        return JSONResponse(status_code=400, content={
            "error": {"message": "model is required", "type": "invalid_request_error"}
        })

    provider_name = determine_provider(model)
    clean_model = strip_provider_prefix(model)

    if provider_name == "ollama":
        ollama_payload = {
            "model": clean_model,
            "prompt": prompt,
            "stream": False,
        }
        if max_tokens:
            ollama_payload["options"] = {"num_predict": max_tokens}

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                r = await client.post(OLLAMA_BASE_URL + "/api/generate", json=ollama_payload)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return JSONResponse(status_code=502, content={
                "error": {"message": "Ollama error: " + str(e), "type": "upstream_error"}
            })

        content = data.get("response", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        latency = int((time.time() - start_time) * 1000)

        asyncio.create_task(log_request(
            source_ip, user_agent, clean_model, "ollama",
            prompt_tokens, completion_tokens, 0.0, latency,
        ))

        return {
            "id": "cmpl-" + uuid.uuid4().hex[:12],
            "object": "text_completion",
            "model": clean_model,
            "choices": [{
                "text": content,
                "index": 0,
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    # Cloud fallback: not supported for legacy completions
    return JSONResponse(status_code=400, content={
        "error": {
            "message": "Legacy completions only supported for Ollama models. Use /v1/chat/completions.",
            "type": "invalid_request_error",
        }
    })


# ---------------------------------------------------------------------------
# Helper: build OpenAI-format response
# ---------------------------------------------------------------------------

def _openai_chat_response(model: str, content: str, prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:12],
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
