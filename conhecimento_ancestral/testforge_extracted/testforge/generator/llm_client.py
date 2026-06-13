"""
TestForge — LLM Client
Thin wrapper around Azure OpenAI (GPT-4o-mini).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("testforge.llm_client")

_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
_KEY = os.getenv("AZURE_OPENAI_KEY", "")
_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")


def chat(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    images: Optional[list[str]] = None,  # list of base64 PNG strings
) -> str:
    """
    Send a chat completion request to Azure OpenAI.
    Returns the assistant text response.
    """
    if not _KEY or not _ENDPOINT:
        raise RuntimeError(
            "Azure OpenAI credentials not set. "
            "Set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT in .env"
        )

    url = f"{_ENDPOINT}/openai/deployments/{_DEPLOYMENT}/chat/completions?api-version={_API_VERSION}"

    user_content: Any
    if images:
        user_content = [{"type": "text", "text": user}]
        for img_b64 in images:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": "low",
                    },
                }
            )
    else:
        user_content = user

    payload = {
        "model": _DEPLOYMENT,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }

    log.debug(f"LLM request → {url} ({len(user)} user chars)")

    with httpx.Client(timeout=120) as client:
        resp = client.post(
            url,
            json=payload,
            headers={
                "api-key": _KEY,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Azure OpenAI error {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    log.debug(
        f"LLM response: {len(content)} chars | "
        f"tokens in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}"
    )
    return content


def extract_code_block(text: str, lang: str = "python") -> str:
    """Extract first code block of given language from LLM response."""
    import re

    pattern = rf"```{lang}\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: strip any markdown fences
    cleaned = re.sub(r"```\w*\n?", "", text)
    cleaned = cleaned.replace("```", "").strip()
    return cleaned
