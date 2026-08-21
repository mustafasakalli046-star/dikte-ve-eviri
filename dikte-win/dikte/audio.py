"""Mikrofon kaydi (Windows, sounddevice/WASAPI uzerinden).

Orijinal projede platforma gore pw-record/ffmpeg secilirdi; burada tek
platform oldugu icin dogrudan sounddevice kullanilir.
"""

from __future__ import annotations

import queue
import threading
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # whisper.cpp ve cogu STT API'si bunu bekler
CHANNELS = 1
DTYPE = "int16"


@dataclass
class Recording:
    samples: np.ndarray  # int16, mono
    samplerate: int = SAMPLE_RATE

    def to_wav(self, path: Path) -> Path:
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # int16
            wf.setframerate(self.samplerate)
            wf.writeframes(self.samples.tobytes())
        return path

    def duration_s(self) -> float:
        return len(self.samples) / float(self.samplerate)


class MicRecorder:
    """Ayri bir thread'de mikrofonu okuyup blok blok biriktirir.

    Kullanim:
        rec = MicRecorder()
        rec.start()
        ... kullanici tekrar kisayola basana kadar bekle ...
        recording = rec.stop()
    """

    def __init__(self, samplerate: int = SAMPLE_RATE, device: int | None = None):
        self.samplerate = samplerate
        self.device = device
        self._q: queue.Queue = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._paused = threading.Event()

    def _callback(self, indata, frames, time_info, status):
        if self._paused.is_set():
            return
        self._q.put(indata.copy())

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=CHANNELS,
            dtype=DTYPE,
            device=self.device,
            callback=self._callback,
        )
        self._stream.start()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def stop(self) -> Recording:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        chunks = []
        while not self._q.empty():
            chunks.append(self._q.get())
        if chunks:
            samples = np.concatenate(chunks, axis=0).reshape(-1)
        else:
            samples = np.zeros((0,), dtype=np.int16)
        return Recording(samples=samples, samplerate=self.samplerate)


def list_input_devices() -> list[str]:
    return [d["name"] for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]


def list_loopback_devices() -> list[str]:
    """Windows WASAPI loopback (hoparlor cikisini kayit) icin aday cihazlar.

    Toplanti modunda konusmaci sesini yakalamak icin kullanilir. Gercek
    loopback yakalama 'soundcard' paketi ile yapilir (meeting.py'ye bakiniz);
    burada sadece isim listesi donuyoruz.
    """
    try:
        import soundcard as sc

        return [spk.name for spk in sc.all_speakers()]
    except Exception:
        return []
