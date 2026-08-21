"""Sistem tepsisi simgesi ve menusu (pystray)."""

from __future__ import annotations

from typing import Callable

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem


def _make_icon_image(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=color)
    return img


ICONS = {
    "idle": _make_icon_image("#4a4a4a"),
    "recording": _make_icon_image("#e0473a"),
    "busy": _make_icon_image("#e0a83a"),
    "error": _make_icon_image("#e0a83a"),
}


class TrayApp:
    def __init__(
        self,
        on_toggle_record: Callable[[], None],
        on_cancel: Callable[[], None],
        on_ask_agent: Callable[[], None],
        on_toggle_meeting: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        menu = Menu(
            MenuItem("Kaydi baslat/durdur", on_toggle_record, default=True),
            MenuItem("Kaydi iptal et", on_cancel),
            MenuItem("Ajana sor", on_ask_agent),
            MenuItem("Toplanti kaydini baslat/bitir", on_toggle_meeting),
            Menu.SEPARATOR,
            MenuItem("Ayarlar", on_settings),
            MenuItem("Cikis", on_quit),
        )
        self.icon = Icon("dikte-win", ICONS["idle"], "Dikte", menu)

    def set_status(self, status: str) -> None:
        self.icon.icon = ICONS.get(status, ICONS["idle"])

    def notify(self, title: str, message: str) -> None:
        try:
            self.icon.notify(message, title)
        except Exception:
            pass  # bazi Windows surumlerinde bildirim engellenmis olabilir

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()
