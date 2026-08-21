"""Genel (global) kisayol dinleyicisi.

Windows'ta 'keyboard' kutuphanesi dusuk seviyeli bir kanca (hook) kurar ve
uygulama arka planda calisirken bile kisayollari yakalar. Orijinal
projedeki coklu-platform 'backend()' secicisinin yerini, tek platform
oldugu icin dogrudan bu modul alir.
"""

from __future__ import annotations

from typing import Callable

import keyboard

from .config import Config


class HotkeyManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._handles: list = []

    def register(
        self,
        on_record: Callable[[], None],
        on_cancel: Callable[[], None],
        on_translate: Callable[[], None],
    ) -> None:
        self._handles.append(keyboard.add_hotkey(self.cfg.record_hotkey, on_record))
        self._handles.append(keyboard.add_hotkey(self.cfg.cancel_hotkey, on_cancel))
        self._handles.append(keyboard.add_hotkey(self.cfg.translate_hotkey, on_translate))

    def unregister_all(self) -> None:
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except (KeyError, ValueError):
                pass
        self._handles.clear()
