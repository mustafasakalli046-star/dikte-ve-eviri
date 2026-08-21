"""Komut satiri: orijinal projedeki gibi her ozelligin bir komutu var, ama
sadelestirilmis. `python -m dikte <komut>` seklinde cagrilir.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config as cfgmod


def _cmd_settings(args: argparse.Namespace) -> None:
    from .settings_ui import SettingsWindow

    cfg = cfgmod.load_config()
    SettingsWindow(cfg).show()


def _cmd_transcribe(args: argparse.Namespace) -> None:
    from .filetranscribe import FileTranscribeError, transcribe_file

    cfg = cfgmod.load_config()
    path = Path(args.file)
    if not path.exists():
        print(f"Dosya bulunamadi: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        text = transcribe_file(path, cfg, as_srt=args.srt)
    except FileTranscribeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    out = path.with_suffix(".srt" if args.srt else ".txt")
    out.write_text(text, encoding="utf-8")
    print(f"Yazildi: {out}")


def _cmd_record(args: argparse.Namespace) -> None:
    import time

    from .audio import MicRecorder
    from .worker import DictationWorker

    cfg = cfgmod.load_config()
    worker = DictationWorker(cfg, on_status=lambda s, d="": print(f"[{s}] {d}"))
    worker.start()
    time.sleep(args.seconds)
    worker.stop_and_process()


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="dikte")
    sub = parser.add_subparsers(dest="command", required=True)

    p_settings = sub.add_parser("settings", help="Ayarlar penceresini ac")
    p_settings.set_defaults(func=_cmd_settings)

    p_record = sub.add_parser("record", help="Belirli sure kayit yap ve isle")
    p_record.add_argument("--seconds", type=float, default=8.0)
    p_record.set_defaults(func=_cmd_record)

    p_tr = sub.add_parser("transcribe", help="Bir ses/video dosyasini transkribe et")
    p_tr.add_argument("file")
    p_tr.add_argument("--srt", action="store_true")
    p_tr.set_defaults(func=_cmd_transcribe)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
