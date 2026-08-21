"""Ingilizce ceviri ozelligi.

Istenen davranis: bir kisayola (varsayilan Ctrl+Alt+V, bkz. config.py'deki
not) basildiginda panodaki (ya da son diktenin) metni Ingilizce'ye cevirip
panoya koyar ve otomatik yapistirir. Ayni LLM katmani (llm.chat) kullanilir,
boylece yerel llama.cpp ya da OpenRouter ile calisir.
"""

from __future__ import annotations

from .config import Config
from .llm import LLMError, chat

SYSTEM_PROMPT = (
    "Sana verilen metni akici, dogal Ingilizce'ye cevir. Anlami degistirme, "
    "yorum ekleme. Sadece ceviriyi dondur."
)


class TranslateError(Exception):
    pass


def translate_to_english(text: str, cfg: Config) -> str:
    if not text.strip():
        raise TranslateError("Cevrilecek metin bos.")
    try:
        return chat(SYSTEM_PROMPT, text, cfg)
    except LLMError as e:
        raise TranslateError(str(e)) from e
