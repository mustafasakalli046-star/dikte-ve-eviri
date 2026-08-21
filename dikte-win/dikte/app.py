"""Giris noktasi: tepsi simgesini, genel kisayollari ve dikte/toplanti/ceviri
hatlarini birbirine baglar. `python -m dikte` bunu calistirir.
"""

from __future__ import annotations

import threading

import pyperclip

from . import agent, config as cfgmod, meeting, translate
from .hotkey import HotkeyManager
from .settings_ui import SettingsWindow
from .tray import TrayApp
from .worker import DictationWorker


class App:
    def __init__(self):
        self.cfg = cfgmod.load_config()
        self.worker = DictationWorker(self.cfg, on_status=self._on_worker_status)
        self.hotkeys = HotkeyManager(self.cfg)
        self.tray = TrayApp(
            on_toggle_record=self._toggle_record,
            on_cancel=self._cancel_record,
            on_ask_agent=self._ask_agent,
            on_toggle_meeting=self._toggle_meeting,
            on_settings=self._open_settings,
            on_quit=self._quit,
        )
        self._meeting_recorder: meeting.MeetingRecorder | None = None
        self._meeting_active = False
        self._agent_mode_next = False  # bir sonraki kayit ajana mi gidecek

    # --- dikte ---
    def _toggle_record(self, icon=None, item=None) -> None:
        if self.worker.is_recording:
            threading.Thread(target=self.worker.stop_and_process, daemon=True).start()
        else:
            self.worker.start()

    def _cancel_record(self, icon=None, item=None) -> None:
        self.worker.cancel()

    def _on_worker_status(self, status: str, detail: str = "") -> None:
        self.tray.set_status("recording" if status == "recording" else
                              "busy" if status in ("transcribing", "cleaning") else
                              "error" if status == "error" else "idle")
        if status == "error":
            self.tray.notify("Dikte - Hata", detail)
        elif status == "empty":
            self.tray.notify("Dikte", detail)

    # --- ajan ---
    def _ask_agent(self, icon=None, item=None) -> None:
        """Mikrofonu ajan icin kaydeder: transkribe eder, ajana gonderir."""
        def flow():
            from .audio import MicRecorder
            import time as _t

            rec = MicRecorder()
            rec.start()
            self.tray.set_status("recording")
            # Basit yaklasim: ikinci kez ayni menuye tiklanana kadar bekleyecek
            # bir arayuz yerine, sabit bir sure sonra otomatik durdurur.
            # Gercek kullanimda record_hotkey ile de tetiklenebilir; burada
            # tepsi menusunden tetiklenen akis 6 saniyelik bir kayit alir.
            _t.sleep(6)
            recording = rec.stop()
            from . import vad as vadmod
            from .transcribe import transcribe, TranscribeError
            import tempfile
            from pathlib import Path

            if not vadmod.has_speech(recording.samples, recording.samplerate, self.cfg):
                self.tray.set_status("idle")
                self.tray.notify("Dikte", "Konusma algilanmadi.")
                return
            with tempfile.TemporaryDirectory() as td:
                wav = Path(td) / "cmd.wav"
                recording.to_wav(wav)
                try:
                    text = transcribe(wav, self.cfg)
                except TranscribeError as e:
                    self.tray.notify("Dikte - Hata", str(e))
                    self.tray.set_status("idle")
                    return
            self.tray.set_status("busy")
            try:
                answer = agent.dictate_as_command(text, self.cfg)
                self.tray.notify("Ajan yanitladi", answer[:200])
            except agent.AgentError as e:
                self.tray.notify("Dikte - Ajan hatasi", str(e))
            self.tray.set_status("idle")

        threading.Thread(target=flow, daemon=True).start()

    # --- toplanti ---
    def _toggle_meeting(self, icon=None, item=None) -> None:
        if not self._meeting_active:
            self._meeting_recorder = meeting.MeetingRecorder()
            self._meeting_recorder.start()
            self._meeting_active = True
            self.tray.set_status("recording")
            self.tray.notify("Dikte", "Toplanti kaydi basladi.")
        else:
            def flow():
                mic, sysaudio = self._meeting_recorder.stop()
                self._meeting_active = False
                self.tray.set_status("busy")
                result = meeting.process_meeting(mic, sysaudio, self.cfg)
                self.tray.set_status("idle")
                self.tray.notify("Dikte", f"Tutanak hazir: {result.raw_dir}")

            threading.Thread(target=flow, daemon=True).start()

    # --- ceviri (Ctrl+Alt+V / ayarlardan degistirilebilir) ---
    def _on_translate_hotkey(self) -> None:
        def flow():
            text = pyperclip.paste()
            if not text or not text.strip():
                self.tray.notify("Dikte", "Pano bos, cevrilecek metin yok.")
                return
            self.tray.set_status("busy")
            try:
                translated = translate.translate_to_english(text, self.cfg)
            except translate.TranslateError as e:
                self.tray.notify("Dikte - Ceviri hatasi", str(e))
                self.tray.set_status("idle")
                return
            from . import clipboard

            clipboard.copy_and_paste(translated)
            self.tray.set_status("idle")

        threading.Thread(target=flow, daemon=True).start()

    # --- ayarlar ---
    def _open_settings(self, icon=None, item=None) -> None:
        def flow():
            win = SettingsWindow(self.cfg, on_save=self._on_settings_saved)
            win.show()

        threading.Thread(target=flow, daemon=True).start()

    def _on_settings_saved(self, cfg: cfgmod.Config) -> None:
        self.cfg = cfg
        self.worker.cfg = cfg
        # Kisayollar degismis olabilir: yeniden kaydet
        self.hotkeys.unregister_all()
        self.hotkeys.register(self._toggle_record, self._cancel_record, self._on_translate_hotkey)

    # --- cikis ---
    def _quit(self, icon=None, item=None) -> None:
        self.hotkeys.unregister_all()
        self.tray.stop()

    def run(self) -> None:
        self.hotkeys.register(self._toggle_record, self._cancel_record, self._on_translate_hotkey)
        self.tray.run()  # bloklar; tepsi simgesi kapatilana kadar calisir


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
