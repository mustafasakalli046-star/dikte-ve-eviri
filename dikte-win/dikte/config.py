"""Ayarlarin okunmasi ve yazilmasi.

Ayarlar %APPDATA%\\Dikte\\config.json dosyasinda tutulur. Orijinal projedeki
gibi API anahtarlari da bu dosyada saklanir; burada ek olarak ortam
degiskenlerinden (OPENAI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY) fallback
yapilir.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "Dikte"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


def data_dir() -> Path:
    d = config_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def meetings_dir() -> Path:
    d = data_dir() / "meetings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def history_dir() -> Path:
    d = data_dir() / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Config:
    # Kisayollar (keyboard kutuphanesinin anladigi format)
    record_hotkey: str = "ctrl+space"
    cancel_hotkey: str = "ctrl+alt+space"
    translate_hotkey: str = "ctrl+alt+v"  # Not: bkz. README - duz 'ctrl+v'
                                            # sistem yapistirmasinin onune
                                            # gecer, o yuzden varsayilan farkli;
                                            # isterseniz "ctrl+v" yapabilirsiniz.

    # Transkripsiyon: "local" (whisper.cpp server), "openai", "groq"
    transcriber: str = "openai"
    whisper_server_url: str = "http://127.0.0.1:8080"
    transcribe_model: str = "gpt-4o-transcribe"

    # Temizlik / ceviri / tutanak icin kullanilan LLM: "local" (llama.cpp
    # server) ya da "openrouter"
    cleanup_provider: str = "openrouter"
    cleanup_enabled: bool = True
    llama_server_url: str = "http://127.0.0.1:8081"
    openrouter_model: str = "google/gemini-3.5-flash-lite"

    # Ajan modu: "claude", "codex", "openrouter"
    agent_provider: str = "claude"
    agent_working_dir: str = str(Path.home())

    # API anahtarlari (bos ise ortam degiskeninden okunur)
    openai_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Sessizlik filtresi (VAD)
    vad_rise_db: float = 10.0          # gurultu tabanindan kac dB yukselmeli
    vad_min_duration_s: float = 0.3    # en az bu sure boyunca
    vad_floor_dbfs: float = -55.0      # ya da mutlak seviye bunun ustunde olmali

    # Ozel isimler / sozluk: STT'ye ipucu, temizlik modeline referans
    glossary: list[str] = field(default_factory=list)

    # Dil
    language: str = "tr"

    # Gecmis boyutu (dikte sayisi)
    history_limit: int = 200

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Config":
        base = Config()
        for k, v in d.items():
            if hasattr(base, k):
                setattr(base, k, v)
        return base

    # --- API anahtari cozumleme (config -> ortam degiskeni) ---
    def resolve_key(self, name: str) -> str:
        direct = getattr(self, name, "") or ""
        if direct:
            return direct
        env_name = {
            "openai_api_key": "OPENAI_API_KEY",
            "groq_api_key": "GROQ_API_KEY",
            "openrouter_api_key": "OPENROUTER_API_KEY",
        }.get(name)
        if env_name:
            return os.environ.get(env_name, "")
        return ""


def load_config() -> Config:
    p = config_path()
    if not p.exists():
        cfg = Config()
        save_config(cfg)
        return cfg
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return Config.from_dict(raw)
    except Exception:
        # Bozuk dosya: varsayilanlara don, mevcut dosyayi ezme
        return Config()


def save_config(cfg: Config) -> None:
    p = config_path()
    p.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass  # Windows'ta chmod'un etkisi sinirlidir, sessizce gec
