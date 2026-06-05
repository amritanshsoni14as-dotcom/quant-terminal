"""LLM abstraction for Modules 11 & 12.

Uses a local Ollama model by default (zero cost, self-hosted). If
ANTHROPIC_API_KEY is set, it transparently switches to Claude — no other code
changes. Everything degrades gracefully if no engine is reachable.
"""
from __future__ import annotations

import httpx

from app.core.config import settings


def provider() -> str:
    if settings.GROQ_API_KEY:
        return "groq"
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    return "ollama"


def status() -> dict:
    p = provider()
    if p == "groq":
        return {"provider": "groq", "model": settings.GROQ_MODEL, "available": True}
    if p == "anthropic":
        return {"provider": "anthropic", "model": "claude", "available": True}
    # Probe Ollama.
    try:
        r = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        ready = any(settings.OLLAMA_MODEL.split(":")[0] in m for m in models)
        return {"provider": "ollama", "model": settings.OLLAMA_MODEL,
                "available": ready, "installed_models": models}
    except Exception as exc:  # noqa: BLE001
        return {"provider": "ollama", "model": settings.OLLAMA_MODEL,
                "available": False, "error": str(exc)}


def generate(prompt: str, system: str = "", temperature: float = 0.2,
             max_tokens: int = 700, timeout: int = 240) -> str:
    """Return the model's completion text. Raises on hard failure."""
    p = provider()
    if p == "groq":
        return _groq(prompt, system, temperature, max_tokens)
    if p == "anthropic":
        return _anthropic(prompt, system, temperature, max_tokens)
    return _ollama(prompt, system, temperature, max_tokens, timeout)


def _groq(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    """Groq cloud (free tier) — OpenAI-compatible chat completions."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _ollama(prompt: str, system: str, temperature: float, max_tokens: int, timeout: int) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = httpx.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()


def _anthropic(prompt: str, system: str, temperature: float, max_tokens: int) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text").strip()
