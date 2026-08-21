"""Toplanti kaydi: mikrofon ve hoparlor cikisini ayni anda kaydeder, ikisini
ayri ayri parcalar halinde transkribe edip zaman damgasina gore
birlestirir, sonra bir LLM'e tutanak (kararlar, aksiyon maddeleri, acik
sorular) cikarttirir.

Windows'ta hoparlor cikisini kaydetmek (loopback) standart sounddevice ile
yapilamaz; bunun icin 'soundcard' paketi ve WASAPI loopback kullanilir.
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import config as cfgmod
from . import vad
from .audio import SAMPLE_RATE, Recording
from .llm import LLMError, chat
from .transcribe import TranscribeError, transcribe

SEGMENT_SECONDS = 20  # her parcanin uzunlugu; kucuk tutmak zaman damgasini iyilestirir

MINUTES_SYSTEM_PROMPT = (
    "Sana zaman damgali, iki kanaldan (Ben / Karsi taraf) gelen bir toplanti "
    "transkripti verilecek. Bundan kisa bir tutanak cikar: Kararlar, "
    "Aksiyon Maddeleri (kim/ne), Acik Sorular. Baslik disinda yorum ekleme."
)


@dataclass
class MeetingSegment:
    speaker: str  # "Ben" (mikrofon) ya da "Karsi taraf" (hoparlor)
    t_start: float
    text: str


@dataclass
class MeetingResult:
    transcript: list[MeetingSegment] = field(default_factory=list)
    minutes: str = ""
    raw_dir: Path | None = None

    def transcript_text(self) -> str:
        lines = []
        for seg in sorted(self.transcript, key=lambda s: s.t_start):
            mm, ss = divmod(int(seg.t_start), 60)
            lines.append(f"[{mm:02d}:{ss:02d}] {seg.speaker}: {seg.text}")
        return "\n".join(lines)


class MeetingRecorder:
    """Mikrofon + sistem sesini eszamanli kaydeder."""

    def __init__(self, samplerate: int = SAMPLE_RATE):
        self.samplerate = samplerate
        self._mic_frames: list[np.ndarray] = []
        self._sys_frames: list[np.ndarray] = []
        self._mic_stream = None
        self._sys_recorder_thread = None
        self._stop_flag = False
        self._t0 = 0.0

    def start(self) -> None:
        import sounddevice as sd

        self._t0 = time.time()
        self._stop_flag = False

        def mic_cb(indata, frames, time_info, status):
            self._mic_frames.append(indata.copy())

        self._mic_stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, dtype="int16", callback=mic_cb
        )
        self._mic_stream.start()

        # Sistem sesi (loopback) - soundcard kutuphanesi ile; kurulu degilse
        # ya da uygun cihaz bulunamazsa toplanti sadece mikrofonla devam eder.
        import threading

        self._sys_recorder_thread = threading.Thread(target=self._record_loopback, daemon=True)
        self._sys_recorder_thread.start()

    def _record_loopback(self) -> None:
        try:
            import soundcard as sc
        except ImportError:
            return
        try:
            speaker = sc.default_speaker()
            mic = sc.get_microphone(speaker.name, include_loopback=True)
        except Exception:
            return
        try:
            with mic.recorder(samplerate=self.samplerate, channels=1) as rec:
                while not self._stop_flag:
                    data = rec.record(numframes=self.samplerate // 10)  # ~100ms
                    pcm16 = np.clip(data[:, 0] * 32768.0, -32768, 32767).astype(np.int16)
                    self._sys_frames.append(pcm16.reshape(-1, 1))
        except Exception:
            return

    def stop(self) -> tuple[Recording, Recording]:
        self._stop_flag = True
        if self._mic_stream is not None:
            self._mic_stream.stop()
            self._mic_stream.close()
        if self._sys_recorder_thread is not None:
            self._sys_recorder_thread.join(timeout=2.0)

        mic = np.concatenate(self._mic_frames, axis=0).reshape(-1) if self._mic_frames else np.zeros((0,), dtype=np.int16)
        sysaudio = np.concatenate(self._sys_frames, axis=0).reshape(-1) if self._sys_frames else np.zeros((0,), dtype=np.int16)
        return Recording(mic, self.samplerate), Recording(sysaudio, self.samplerate)


def _segments_from(recording: Recording, speaker_label: str, cfg: cfgmod.Config, tmpdir: Path) -> list[MeetingSegment]:
    out: list[MeetingSegment] = []
    seg_len = int(SEGMENT_SECONDS * recording.samplerate)
    if seg_len <= 0 or recording.samples.size == 0:
        return out
    n_segments = max(1, len(recording.samples) // seg_len + (1 if len(recording.samples) % seg_len else 0))
    for i in range(n_segments):
        chunk = recording.samples[i * seg_len : (i + 1) * seg_len]
        if chunk.size == 0:
            continue
        if not vad.has_speech(chunk, recording.samplerate, cfg):
            continue
        seg_wav = tmpdir / f"{speaker_label}_{i}.wav"
        Recording(chunk, recording.samplerate).to_wav(seg_wav)
        try:
            text = transcribe(seg_wav, cfg)
        except TranscribeError:
            continue
        if text.strip():
            out.append(MeetingSegment(speaker=speaker_label, t_start=i * SEGMENT_SECONDS, text=text.strip()))
    return out


def process_meeting(mic: Recording, sysaudio: Recording, cfg: cfgmod.Config) -> MeetingResult:
    result = MeetingResult()
    save_dir = cfgmod.meetings_dir() / time.strftime("%Y%m%d-%H%M%S")
    save_dir.mkdir(parents=True, exist_ok=True)
    mic.to_wav(save_dir / "mic.wav")
    if sysaudio.samples.size:
        sysaudio.to_wav(save_dir / "speaker.wav")
    result.raw_dir = save_dir

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result.transcript += _segments_from(mic, "Ben", cfg, tmp)
        if sysaudio.samples.size:
            result.transcript += _segments_from(sysaudio, "Karsi taraf", cfg, tmp)

    transcript_text = result.transcript_text()
    (save_dir / "transcript.txt").write_text(transcript_text, encoding="utf-8")

    if transcript_text.strip():
        try:
            result.minutes = chat(MINUTES_SYSTEM_PROMPT, transcript_text, cfg)
            (save_dir / "minutes.md").write_text(result.minutes, encoding="utf-8")
        except LLMError as e:
            result.minutes = f"(Tutanak olusturulamadi: {e})"

    return result
