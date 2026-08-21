"""Pano ve yapistirma islemleri (Windows).

pyperclip panoyu yonetir, keyboard kutuphanesi Ctrl+V'yi aktif pencereye
gonderir - orijinal projedeki paste.py'nin ydotool/CoreGraphics
sarmalayicilarinin Windows-only karsiligi.
"""

from __future__ import annotations

import time

import keyboard
import pyperclip


def copy(text: str) -> None:
    pyperclip.copy(text)


def paste() -> None:
    # Panonun gercekten guncellenmis olmasi icin kucuk bir bekleme
    time.sleep(0.05)
    keyboard.send("ctrl+v")


def copy_and_paste(text: str) -> None:
    copy(text)
    paste()
