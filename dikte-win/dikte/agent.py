"""Ajan modu: dikteyi yapistirmak yerine bir komut olarak calistirir.

Orijinal projedeki gibi uc secenek:
  - "claude": `claude -p "<metin>"` (Claude Code CLI, PATH'te olmali)
  - "codex":  `codex exec "<metin>"` (Codex CLI, PATH'te olmali)
  - "openrouter": CLI yoksa duz soru-cevap fallback'i, llm.chat kullanir
"""

from __future__ import annotations

import shutil
import subprocess

from . import clipboard
from .config import Config
from .llm import LLMError, chat

AGENT_SYSTEM_PROMPT = (
    "Kullanicidan sesli bir komut aldin. Iste ne isteniyorsa onu yap ve "
    "kisa, net bir yanit ver."
)


class AgentError(Exception):
    pass


def run_agent(text: str, cfg: Config) -> str:
    provider = cfg.agent_provider
    if provider == "claude":
        return _run_cli("claude", ["-p", text], cfg)
    if provider == "codex":
        return _run_cli("codex", ["exec", text], cfg)
    # openrouter fallback
    try:
        return chat(AGENT_SYSTEM_PROMPT, text, cfg)
    except LLMError as e:
        raise AgentError(str(e)) from e


def _run_cli(binary: str, args: list[str], cfg: Config) -> str:
    if shutil.which(binary) is None:
        raise AgentError(f"'{binary}' PATH'te bulunamadi. Kurulu degilse ayarlardan "
                          f"OpenRouter'a gecebilirsiniz.")
    try:
        result = subprocess.run(
            [binary, *args],
            cwd=cfg.agent_working_dir or None,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise AgentError(f"'{binary}' zaman asimina ugradi.") from e
    if result.returncode != 0:
        raise AgentError(f"'{binary}' hata kodu {result.returncode}: {result.stderr[:300]}")
    return result.stdout.strip()


def dictate_as_command(text: str, cfg: Config) -> str:
    """Ajana gonderir, yaniti panoya kopyalayip yapistirir, yaniti dondurur."""
    answer = run_agent(text, cfg)
    clipboard.copy_and_paste(answer if answer else "(Ajan bos yanit dondurdu.)")
    return answer
