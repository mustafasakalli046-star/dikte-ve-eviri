"""Ham transkripti temizler: kekemelik/tekrar cikarma, noktalama, ozel isim
duzeltmesi (sozluk baglaminda).

Temizlik basarisiz olursa istisna firlatilmaz: cagiran taraf (worker.py)
ham metni kullanmaya devam eder ve hatayi ayri raporlar - orijinal
projedeki "basarisiz temizlik asla sessiz degildir" davranisiyla ayni.
"""

from __future__ import annotations

from .config import Config
from .llm import LLMError, chat

SYSTEM_PROMPT = (
    "Sana sesli dikte edilmis ham bir transkript verilecek. Gorevin:\n"
    "1) 'ıı', 'şey', tekrarlar ve yarim kalan cumleleri temizle.\n"
    "2) Noktalama ve buyuk harfleri duzelt.\n"
    "3) Asagida verilen ozel isim listesindeki kelimelere fonetik olarak "
    "benzeyen ama yanlis yazilmis kelimeleri, baglam acikca isaret ediyorsa "
    "duzelt. Baglam belirsizse kelimeye dokunma.\n"
    "4) Anlami veya soylenmeyen hicbir seyi ekleme/cikarma.\n"
    "Sadece temizlenmis metni dondur, baska aciklama ekleme."
)


def clean_text(raw_text: str, cfg: Config) -> str:
    if not cfg.cleanup_enabled or not raw_text.strip():
        return raw_text

    glossary_block = ""
    if cfg.glossary:
        glossary_block = "\n\nOzel isim sozlugu: " + ", ".join(cfg.glossary)

    try:
        return chat(SYSTEM_PROMPT + glossary_block, raw_text, cfg)
    except LLMError:
        # Cagiran taraf ham metni kullanacak; burada sessizce yutmuyoruz,
        # hatayi tekrar yukseltiyoruz ki worker.py durumu bildirebilsin.
        raise
