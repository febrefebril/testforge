"""TestForge — LLM Client.

Thin wrapper around Azure OpenAI / OpenAI.
Auto-detects provider via environment variables.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import httpx

log = logging.getLogger("testforge.llm_client")


def _get_config() -> dict:
    """Detect LLM provider from environment."""
    # Azure OpenAI (preferred)
    azure_key = os.getenv("AZURE_OPENAI_KEY", "")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    # OpenAI direct
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    return {
        "provider": "azure" if (azure_key and azure_endpoint) else ("openai" if openai_key else ""),
        "azure_key": azure_key,
        "azure_endpoint": azure_endpoint,
        "azure_deployment": azure_deployment,
        "azure_api_version": azure_api_version,
        "openai_key": openai_key,
        "openai_model": openai_model,
    }


def chat(
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 500,
    images: Optional[list[str]] = None,  # list of base64 PNG strings
) -> str:
    """Send chat completion request. Returns assistant text response."""
    config = _get_config()

    if config["provider"] == "azure":
        return _chat_azure(config, system, user, temperature, max_tokens, images)
    elif config["provider"] == "openai":
        return _chat_openai(config, system, user, temperature, max_tokens, images)
    else:
        raise RuntimeError(
            "No LLM provider configured. Set AZURE_OPENAI_KEY+AZURE_OPENAI_ENDPOINT "
            "or OPENAI_API_KEY in environment."
        )


def is_available() -> bool:
    """Check if any LLM provider is configured."""
    config = _get_config()
    return config["provider"] != ""


def _chat_azure(
    config: dict,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    images: Optional[list[str]],
) -> str:
    url = (
        f"{config['azure_endpoint']}/openai/deployments/"
        f"{config['azure_deployment']}/chat/completions"
        f"?api-version={config['azure_api_version']}"
    )

    user_content: Any
    if images:
        user_content = [{"type": "text", "text": user}]
        for img_b64 in images:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "low"},
            })
    else:
        user_content = user

    payload = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }

    log.debug("LLM request → Azure OpenAI (%d user chars)", len(user))

    with httpx.Client(timeout=120) as client:
        resp = client.post(
            url,
            json=payload,
            headers={"api-key": config["azure_key"], "Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Azure OpenAI error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    log.debug(
        "LLM response: %d chars | tokens in=%d out=%d",
        len(content),
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )
    return content


def _chat_openai(
    config: dict,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    images: Optional[list[str]],
) -> str:
    url = "https://api.openai.com/v1/chat/completions"

    user_content: Any
    if images:
        user_content = [{"type": "text", "text": user}]
        for img_b64 in images:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "low"},
            })
    else:
        user_content = user

    payload = {
        "model": config["openai_model"],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }

    log.debug("LLM request → OpenAI (%d user chars)", len(user))

    with httpx.Client(timeout=120) as client:
        resp = client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {config['openai_key']}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    log.debug(
        "LLM response: %d chars | tokens in=%d out=%d",
        len(content),
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )
    return content


def extract_code_block(text: str, lang: str = "python") -> str:
    """Extract first code block of given language from LLM response."""
    pattern = rf"```{lang}\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    cleaned = re.sub(r"```\w*\n?", "", text)
    cleaned = cleaned.replace("```", "").strip()
    return cleaned
