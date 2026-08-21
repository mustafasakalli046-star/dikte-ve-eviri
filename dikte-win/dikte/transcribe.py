"""Konusmayi metne cevirme: yerel whisper.cpp server ya da bulut (OpenAI/Groq).

Yerel mod icin whisper.cpp'nin 'server' binary'sinin ayrica calisiyor
olmasi gerekir (bkz. README - orijinal projedeki gibi burada da otomatik
indirme yapilmiyor, bu minimal surumde elle kurulum varsayiliyor).
"""

from __future__ import annotations

from pathlib import Path

import requests

from .config import Config


class TranscribeError(Exception):
    pass


def transcribe(wav_path: Path, cfg: Config, glossary_hint: str = "") -> str:
    if cfg.transcriber == "local":
        return _transcribe_local(wav_path, cfg, glossary_hint)
    if cfg.transcriber == "groq":
        return _transcribe_cloud(
            wav_path,
            url="https://api.groq.com/openai/v1/audio/transcriptions",
            api_key=cfg.resolve_key("groq_api_key"),
            model="whisper-large-v3",
            glossary_hint=glossary_hint,
        )
    # varsayilan: openai-uyumlu bulut
    return _transcribe_cloud(
        wav_path,
        url="https://api.openai.com/v1/audio/transcriptions",
        api_key=cfg.resolve_key("openai_api_key"),
        model=cfg.transcribe_model,
        glossary_hint=glossary_hint,
    )


def _transcribe_local(wav_path: Path, cfg: Config, glossary_hint: str) -> str:
    url = cfg.whisper_server_url.rstrip("/") + "/inference"
    with open(wav_path, "rb") as f:
        files = {"file": (wav_path.name, f, "audio/wav")}
        data = {"language": cfg.language, "prompt": glossary_hint}
        try:
            resp = requests.post(url, files=files, data=data, timeout=120)
        except requests.RequestException as e:
            raise TranscribeError(f"Yerel whisper.cpp sunucusuna ulasilamadi: {e}") from e
    if resp.status_code != 200:
        raise TranscribeError(f"Yerel STT hatasi: {resp.status_code} {resp.text[:200]}")
    body = resp.json()
    return (body.get("text") or "").strip()


def _transcribe_cloud(wav_path: Path, url: str, api_key: str, model: str, glossary_hint: str) -> str:
    if not api_key:
        raise TranscribeError("API anahtari yok (ayarlardan ya da ortam degiskeninden girin).")
    with open(wav_path, "rb") as f:
        files = {"file": (wav_path.name, f, "audio/wav")}
        data = {"model": model}
        if glossary_hint:
            data["prompt"] = glossary_hint
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        except requests.RequestException as e:
            raise TranscribeError(f"STT istegi basarisiz: {e}") from e
    if resp.status_code != 200:
        raise TranscribeError(f"STT hatasi: {resp.status_code} {resp.text[:200]}")
    body = resp.json()
    return (body.get("text") or "").strip()
