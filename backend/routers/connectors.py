"""Universal AI Connector — manage and query AI providers."""

import asyncio
import shutil
import os
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ..providers.registry import get_registry
from ..database import get_db, CostEntry, AIInteraction

router = APIRouter()


class CompleteRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    max_tokens: Optional[int] = 2048


async def _detect_cli_tool(name: str, binary: str, version_cmd: list[str]) -> dict:
    """Detect a CLI tool: check existence, get version and path."""
    path = shutil.which(binary)
    info = {
        "name": name,
        "type": "cli",
        "available": path is not None,
        "version": None,
        "path": path,
    }

    # Special handling for Gemini CLI: check if API key is configured
    if binary == "gemini" and path:
        gemini_key_configured = bool(os.environ.get("GEMINI_API_KEY"))
        info["key_configured"] = gemini_key_configured
        if not gemini_key_configured:
            info["setup_instructions"] = "Set GEMINI_API_KEY environment variable to use Gemini CLI"

    if path:
        try:
            proc = await asyncio.create_subprocess_exec(
                *version_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            output = (stdout or stderr or b"").decode().strip()
            # Take just the first line for cleanliness
            if output:
                info["version"] = output.splitlines()[0]
        except Exception:
            info["version"] = "unknown"
    return info


CLI_TOOLS = [
    ("Claude Code", "claude", ["claude", "--version"]),
    ("Gemini CLI", "gemini", ["gemini", "--version"]),
    ("Aider", "aider", ["aider", "--version"]),
    ("GitHub Copilot CLI", "gh", ["gh", "copilot", "--version"]),
]


@router.get("")
async def list_connectors():
    """List all configured AI providers and their availability."""
    registry = get_registry()
    results = []
    for name, provider in registry.items():
        available = await provider.is_available()
        models = await provider.list_models() if available else []
        results.append({
            "name": name,
            "type": "api",
            "available": available,
            "models": models[:10],
        })
    return results


@router.get("/cli")
async def list_cli_tools():
    """Detect CLI-based AI tools installed on this machine."""
    tasks = [_detect_cli_tool(name, binary, ver_cmd) for name, binary, ver_cmd in CLI_TOOLS]
    return await asyncio.gather(*tasks)


@router.post("/complete")
async def complete(req: CompleteRequest, db=Depends(get_db)):
    """Run a completion on any connected provider or CLI tool."""
    import time as _time

    # Handle CLI tools (Claude Code, Gemini CLI)
    cli_map = {
        "Claude Code": "claude",
        "Gemini CLI": "gemini",
    }
    if req.provider in cli_map:
        binary = cli_map[req.provider]
        start = _time.time()
        try:
            if binary == "claude":
                proc = await asyncio.create_subprocess_exec(
                    "claude", "--print", "--model", req.model, req.prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:  # gemini
                proc = await asyncio.create_subprocess_exec(
                    "gemini", "--model", req.model, "--prompt", req.prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            content = (stdout or b"").decode().strip()
            if not content:
                content = (stderr or b"").decode().strip()
            latency = int((_time.time() - start) * 1000)
            tokens_out = len(content.split())
            tokens_in = len(req.prompt.split())

            # Log interaction for CLI tools
            interaction = AIInteraction(
                provider=req.provider.lower().replace(" ", "_"),
                model=req.model,
                prompt=req.prompt,
                response=content or "No response from CLI",
                tokens_used=tokens_in + tokens_out,
                cost_usd=0.0,
            )
            db.add(interaction)
            await db.commit()

            return {
                "provider": req.provider,
                "model": req.model,
                "content": content or "No response from CLI",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": 0.0,
                "latency_ms": latency,
            }
        except asyncio.TimeoutError:
            return {"error": f"{req.provider} timed out after 60s"}
        except Exception as e:
            return {"error": f"{req.provider} error: {str(e)}"}

    registry = get_registry()
    provider = registry.get(req.provider)
    if not provider:
        return {"error": f"Provider '{req.provider}' not found"}

    response = await provider.complete(req.prompt, req.model, max_tokens=req.max_tokens)

    # Log both CostEntry and AIInteraction
    cost_entry = CostEntry(
        provider=response.provider,
        model=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd=response.cost_usd,
    )
    db.add(cost_entry)

    interaction = AIInteraction(
        provider=response.provider,
        model=response.model,
        prompt=req.prompt,
        response=response.content,
        tokens_used=response.tokens_in + response.tokens_out,
        cost_usd=response.cost_usd,
    )
    db.add(interaction)
    await db.commit()

    return {
        "provider": response.provider,
        "model": response.model,
        "content": response.content,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "cost_usd": response.cost_usd,
        "latency_ms": response.latency_ms,
    }


@router.get("/detect")
async def auto_detect():
    """Auto-detect available AI tools on this machine."""
    detected = {}

    # Check CLI tools
    for tool in ["ollama", "claude", "aider", "gemini"]:
        detected[tool] = shutil.which(tool) is not None

    # Check gh copilot
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh", "copilot", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5)
        detected["gh_copilot"] = proc.returncode == 0
    except Exception:
        detected["gh_copilot"] = False

    # Check Ollama API
    registry = get_registry()
    detected["ollama_api"] = await registry["ollama"].is_available()

    return detected
