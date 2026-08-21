"""Temizlik, ceviri ve tutanak icin ortak LLM cagri katmani.

Iki saglayici destekler:
  - "local": llama.cpp server (OpenAI-uyumlu /v1/chat/completions)
  - "openrouter": OpenRouter API
"""

from __future__ import annotations

import requests

from .config import Config


class LLMError(Exception):
    pass


def chat(system_prompt: str, user_text: str, cfg: Config) -> str:
    if cfg.cleanup_provider == "local":
        return _chat_openai_compatible(
            url=cfg.llama_server_url.rstrip("/") + "/v1/chat/completions",
            api_key="local",
            model="local",
            system_prompt=system_prompt,
            user_text=user_text,
        )
    api_key = cfg.resolve_key("openrouter_api_key")
    if not api_key:
        raise LLMError("OpenRouter API anahtari yok.")
    return _chat_openai_compatible(
        url="https://openrouter.ai/api/v1/chat/completions",
        api_key=api_key,
        model=cfg.openrouter_model,
        system_prompt=system_prompt,
        user_text=user_text,
    )


def _chat_openai_compatible(url: str, api_key: str, model: str, system_prompt: str, user_text: str) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "local":
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMError(f"LLM istegi basarisiz: {e}") from e
    if resp.status_code != 200:
        raise LLMError(f"LLM hatasi: {resp.status_code} {resp.text[:200]}")
    body = resp.json()
    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise LLMError(f"Beklenmeyen LLM yaniti: {body}") from e
