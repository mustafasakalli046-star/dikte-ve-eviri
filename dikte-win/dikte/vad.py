"""Sessizlik filtresi: kayitta gercekten konusma olup olmadigina karar verir.

Orijinal projedeki mantik: kaydin kendi gurultu tabanindan en az
`rise_db` dB yukselen ve bu yukselisin en az `min_duration_s` sure surdugu
bir bolum yoksa, ya da kaydin en yuksek seviyesi mutlak `floor_dbfs`
esiginin altindaysa, kayit "sessiz" sayilir ve API'ye hic gonderilmez.
Bu, STT modellerinin sessizlige "Thanks for watching" gibi uydurma
cumleler uretmesini engeller.
"""

from __future__ import annotations

import numpy as np

from .config import Config


def _dbfs(samples: np.ndarray) -> float:
    """int16 ornekler icin dBFS (0 dBFS = tam olcek)."""
    if samples.size == 0:
        return -120.0
    rms = np.sqrt(np.mean((samples.astype(np.float64) / 32768.0) ** 2))
    if rms <= 1e-9:
        return -120.0
    return 20.0 * np.log10(rms)


def _frame_levels(samples: np.ndarray, samplerate: int, frame_ms: int = 30) -> np.ndarray:
    frame_len = max(1, int(samplerate * frame_ms / 1000))
    n_frames = len(samples) // frame_len
    if n_frames == 0:
        return np.array([_dbfs(samples)])
    trimmed = samples[: n_frames * frame_len].reshape(n_frames, frame_len)
    return np.array([_dbfs(f) for f in trimmed])


def has_speech(samples: np.ndarray, samplerate: int, cfg: Config) -> bool:
    """Kayitta konusma olma ihtimali varsa True doner."""
    if samples.size == 0:
        return False

    peak = _dbfs(samples)
    if peak < cfg.vad_floor_dbfs:
        return False

    levels = _frame_levels(samples, samplerate)
    noise_floor = float(np.percentile(levels, 10))  # sessiz kisimlarin tahmini seviyesi

    frame_ms = 30
    min_frames = max(1, int((cfg.vad_min_duration_s * 1000) / frame_ms))
    risen = levels >= (noise_floor + cfg.vad_rise_db)

    # ust uste en az min_frames kadar "yukselmis" cerceve var mi?
    run = 0
    for r in risen:
        run = run + 1 if r else 0
        if run >= min_frames:
            return True
    return False
