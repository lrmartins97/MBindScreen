"""Entry point of the M-BIND touchscreen."""
from __future__ import annotations

import argparse
import logging
import sys

from configfile import load_config
from lib.panels.mainWindow import MainWindow
from lib.simulator import SimulatedPrinter
from lib.utils.theme import QSS
from logger import install_crash_handler, setup_logging
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger("MBindScreen")
WINDOW_SIZE = (800, 480)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ecrã tátil da M-BIND")
    parser.add_argument("--fullscreen", action="store_true", help="on the printer screen")
    parser.add_argument("--simulate", action="store_true", help="fake printer, no Moonraker")
    parser.add_argument("--host", help="Moonraker host (default: MBindScreen.cfg)")
    parser.add_argument("--port", type=int, help="Moonraker port")
    parser.add_argument("--debug", action="store_true", help="log every Moonraker request")
    parser.add_argument(
        "--read-only", action="store_true", help="trial: send no commands to the machine"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logfile = setup_logging(logging.DEBUG if args.debug else logging.INFO)
    logger.info("=== MBindScreen starting, log: %s ===", logfile)
    config = load_config()
    if args.host or args.port:
        import dataclasses

        config = dataclasses.replace(
            config, host=args.host or config.host, port=args.port or config.port
        )
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("MBindScreen")
    app.setStyleSheet(QSS)
    api = SimulatedPrinter() if args.simulate else None
    window = MainWindow(config, api, args.read_only)
    install_crash_handler(window.printer.add_alert)
    if args.fullscreen:
        app.setOverrideCursor(QtCore.Qt.CursorShape.BlankCursor)
        window.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
        window.setGeometry(app.primaryScreen().geometry())
        window.showFullScreen()
    else:
        window.setFixedSize(*WINDOW_SIZE)
        window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
