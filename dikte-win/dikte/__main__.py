"""`python -m dikte` giris noktasi.

Argumansiz calistirildiginda tepsi uygulamasini baslatir; ilk argumanla
CLI'ye devreder (bkz. cli.py).
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) > 1:
        from .cli import main as cli_main

        cli_main(sys.argv[1:])
    else:
        from .app import main as app_main

        app_main()


if __name__ == "__main__":
    main()
