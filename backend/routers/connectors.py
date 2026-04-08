"""Universal AI Connector — manage and query AI providers."""

import asyncio
import shutil
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ..providers.registry import get_registry
from ..database import get_db, CostEntry

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
    """Run a completion on any connected provider."""
    registry = get_registry()
    provider = registry.get(req.provider)
    if not provider:
        return {"error": f"Provider '{req.provider}' not found"}

    response = await provider.complete(req.prompt, req.model, max_tokens=req.max_tokens)

    cost_entry = CostEntry(
        provider=response.provider,
        model=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd=response.cost_usd,
    )
    db.add(cost_entry)
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
