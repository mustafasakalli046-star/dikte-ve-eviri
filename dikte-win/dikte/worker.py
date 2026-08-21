"""Ana dikte hattini yurutur: kayit -> VAD -> transkripsiyon -> temizlik ->
pano/yapistirma -> gecmis.

Orijinal projedeki worker.py'nin sadelestirilmis karsiligi. Durum
degisiklikleri `on_status(status: str, detail: str)` geri cagirisiyla
disariya (tray/overlay) bildirilir; status degerleri:
  "recording", "transcribing", "cleaning", "done", "empty", "error"
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from . import clipboard, config as cfgmod, vad
from .audio import MicRecorder, Recording
from .cleanup import clean_text
from .llm import LLMError
from .transcribe import TranscribeError, transcribe


class DictationWorker:
    def __init__(self, cfg: cfgmod.Config, on_status=None):
        self.cfg = cfg
        self.on_status = on_status or (lambda status, detail="": None)
        self._recorder: MicRecorder | None = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording:
            return
        self._recorder = MicRecorder()
        self._recorder.start()
        self._recording = True
        self.on_status("recording")

    def cancel(self) -> None:
        if not self._recording or self._recorder is None:
            return
        self._recorder.stop()
        self._recorder = None
        self._recording = False
        self.on_status("cancelled")

    def stop_and_process(self) -> None:
        """Kaydi durdurur ve tum hatti senkron calistirir.

        Cagiran taraf (app.py) bunu bir arka plan thread'inde cagirmalidir;
        Qt/Tk sinyali gerektirmez, dogrudan fonksiyon donusu kullanilir.
        """
        if not self._recording or self._recorder is None:
            return
        recording = self._recorder.stop()
        self._recorder = None
        self._recording = False
        self._process(recording)

    def _process(self, recording: Recording) -> None:
        if recording.duration_s() < 0.1:
            self.on_status("empty", "Kayit cok kisa.")
            return

        if not vad.has_speech(recording.samples, recording.samplerate, self.cfg):
            self.on_status("empty", "Konusma algilanmadi (sessizlik).")
            return

        self.on_status("transcribing")
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "dikte.wav"
            recording.to_wav(wav_path)
            glossary_hint = ", ".join(self.cfg.glossary)
            try:
                raw_text = transcribe(wav_path, self.cfg, glossary_hint)
            except TranscribeError as e:
                self.on_status("error", str(e))
                return

        if not raw_text.strip():
            self.on_status("empty", "Bos transkript.")
            return

        final_text = raw_text
        cleanup_failed_reason = ""
        if self.cfg.cleanup_enabled:
            self.on_status("cleaning")
            try:
                final_text = clean_text(raw_text, self.cfg)
            except LLMError as e:
                cleanup_failed_reason = str(e)
                final_text = raw_text  # ham metin kaybolmaz

        clipboard.copy_and_paste(final_text)
        self._append_history(raw_text, final_text)

        if cleanup_failed_reason:
            self.on_status("error", f"Temizlik basarisiz, ham metin yapistirildi: {cleanup_failed_reason}")
        else:
            self.on_status("done", final_text)

    def _append_history(self, raw_text: str, final_text: str) -> None:
        hist_dir = cfgmod.history_dir()
        entry = {
            "ts": time.time(),
            "raw": raw_text,
            "final": final_text,
        }
        entries = []
        idx_path = hist_dir / "index.json"
        if idx_path.exists():
            try:
                entries = json.loads(idx_path.read_text(encoding="utf-8"))
            except Exception:
                entries = []
        entries.append(entry)
        entries = entries[-self.cfg.history_limit :]
        idx_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
