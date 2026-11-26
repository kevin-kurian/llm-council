"""Provider dispatch: OpenRouter HTTP plus local subscription CLIs.

Model identifiers are ``<provider>:<model>``:
  openrouter:google/gemini-3-pro-preview   HTTP API (needs OPENROUTER_API_KEY)
  codex:gpt-6.1-sol                        `codex exec` (ChatGPT subscription)
  grok:grok-4.7                            `grok -p` (grok.com subscription)
  agy:gemini-4-hydrogen-high               `agy -p` (Antigravity subscription)

Bare identifiers default to OpenRouter.
"""

import asyncio
import json
import tempfile
from typing import Any, Dict, List, Optional

from .config import REASONING_EFFORT
from .openrouter import query_model as query_openrouter

PROVIDERS = ("openrouter", "codex", "grok", "agy")

# agy rejects --effort when the model slug already ends in an effort level
EFFORT_SUFFIXES = ("low", "medium", "high", "xhigh", "max")

# Agentic CLIs run outside the repo so they cannot touch council code.
CLI_WORKDIR = tempfile.gettempdir()


def parse_model(model: str) -> tuple[str, str]:
    """Split a model identifier into (provider, model_name)."""
    provider, _, name = model.partition(":")
    if name and provider.lower() in PROVIDERS:
        return provider.lower(), name
    return "openrouter", model


def _flatten(messages: List[Dict[str, Any]]) -> str:
    """Collapse chat messages into one prompt string for single-turn CLIs."""
    parts = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        parts.append(f"Assistant:\n{content}" if role == "assistant" else content)
    return "\n\n".join(parts)


async def _run(command: List[str], stdin_text: Optional[str], timeout: float) -> tuple[int, str]:
    """Run a CLI and return (returncode, stdout). stderr is kept for error text."""
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE if stdin_text else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=CLI_WORKDIR,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(stdin_text.encode() if stdin_text else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError(f"timed out after {timeout}s")

    if process.returncode:
        raise RuntimeError(f"exit {process.returncode}: {stderr.decode('utf-8', 'replace')[-400:]}")
    return process.returncode or 0, stdout.decode("utf-8", "replace")


async def query_codex(model: str, messages: List[Dict[str, Any]], timeout: float) -> Optional[Dict[str, Any]]:
    command = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--json", "-C", CLI_WORKDIR]
    if model:
        command += ["-c", f'model="{model}"']
    if REASONING_EFFORT:
        command += ["-c", f'model_reasoning_effort="{REASONING_EFFORT}"']
    command.append("-")  # prompt on stdin

    _, stdout = await _run(command, _flatten(messages), timeout)

    texts = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and item.get("text"):
            texts.append(item["text"])
    if not texts:
        raise RuntimeError("codex returned no agent message")
    return {"content": texts[-1]}


async def query_grok(model: str, messages: List[Dict[str, Any]], timeout: float) -> Optional[Dict[str, Any]]:
    command = ["grok", "--output-format", "json", "--cwd", CLI_WORKDIR, "--disable-web-search"]
    if model:
        command += ["--model", model]
    if REASONING_EFFORT:
        command += ["--reasoning-effort", REASONING_EFFORT]
    command.append("-p")  # prompt on stdin

    _, stdout = await _run(command, _flatten(messages), timeout)
    payload = json.loads(stdout[stdout.index("{"):])
    if not payload.get("text"):
        raise RuntimeError("grok returned no text")
    return {"content": payload["text"], "cost_usd": payload.get("total_cost_usd")}


async def query_agy(model: str, messages: List[Dict[str, Any]], timeout: float) -> Optional[Dict[str, Any]]:
    command = ["agy", "--output-format", "json", "--disable-slash-commands"]
    if model:
        command += ["--model", model]
    if REASONING_EFFORT and model.rsplit("-", 1)[-1] not in EFFORT_SUFFIXES:
        command += ["--effort", REASONING_EFFORT]
    command.append(f"-p={_flatten(messages)}")  # agy print mode has no stdin prompt

    _, stdout = await _run(command, None, timeout)
    payload = json.loads(stdout[stdout.index("{"):])
    if payload.get("status") != "SUCCESS" or not payload.get("response"):
        raise RuntimeError(f"agy status {payload.get('status')}")
    return {"content": payload["response"]}


CLI_HANDLERS = {"codex": query_codex, "grok": query_grok, "agy": query_agy}


async def query_model(model: str, messages: List[Dict[str, Any]], timeout: float = 240.0) -> Optional[Dict[str, Any]]:
    """Query one model through the provider named in its identifier."""
    provider, name = parse_model(model)
    try:
        if provider == "openrouter":
            return await query_openrouter(name, messages, timeout=timeout)
        return await CLI_HANDLERS[provider](name, messages, timeout)
    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, Any]],
    timeout: float = 240.0,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Query several models in parallel across providers."""
    responses = await asyncio.gather(*(query_model(m, messages, timeout=timeout) for m in models))
    return dict(zip(models, responses))
