"""Ses/video dosyalarindan transkript cikarma.

ffmpeg PATH'te bulunmalidir (winget install Gyan.FFmpeg). Uzun dosyalar
sabit uzunlukta parcalara bolunur, her parca ayri transkribe edilir;
istege bagli olarak .srt altyazi ya da duz .txt olarak kaydedilir.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config as cfgmod
from .audio import SAMPLE_RATE
from .transcribe import TranscribeError, transcribe

CHUNK_SECONDS = 60


class FileTranscribeError(Exception):
    pass


def _ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise FileTranscribeError("ffmpeg PATH'te bulunamadi (winget install Gyan.FFmpeg).")


def _probe_duration(path: Path) -> float:
    _ensure_ffmpeg()
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return 0.0
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _extract_chunk(path: Path, start_s: float, dur_s: float, out_wav: Path) -> None:
    _ensure_ffmpeg()
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_s), "-t", str(dur_s), "-i", str(path),
        "-ac", "1", "-ar", str(SAMPLE_RATE), "-vn", str(out_wav),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _format_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_file(path: Path, cfg: cfgmod.Config, as_srt: bool = False) -> str:
    _ensure_ffmpeg()
    duration = _probe_duration(path)
    if duration <= 0:
        # sure alinamadiysa tek parca varsayimiyla dene
        duration = CHUNK_SECONDS

    pieces: list[tuple[float, float, str]] = []  # (start, end, text)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        t = 0.0
        idx = 0
        while t < duration:
            dur = min(CHUNK_SECONDS, duration - t)
            chunk_wav = tmp / f"chunk_{idx}.wav"
            try:
                _extract_chunk(path, t, dur, chunk_wav)
            except subprocess.CalledProcessError as e:
                raise FileTranscribeError(f"ffmpeg hatasi: {e}") from e
            try:
                text = transcribe(chunk_wav, cfg)
            except TranscribeError as e:
                text = f"[transkripsiyon hatasi: {e}]"
            if text.strip():
                pieces.append((t, t + dur, text.strip()))
            t += dur
            idx += 1

    if as_srt:
        lines = []
        for i, (start, end, text) in enumerate(pieces, start=1):
            lines.append(str(i))
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    return "\n".join(f"[{int(s // 60):02d}:{int(s % 60):02d}] {t}" for s, _, t in pieces)
