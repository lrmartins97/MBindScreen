"""Logging and crash capture.

Everything goes to ``~/printer_data/logs/MBindScreen.log``: Moonraker serves that
folder, so the log can be opened from Mainsail without SSH. Native crashes (Qt
segfaults) go to ``MBindScreen_fault.log`` through faulthandler.
"""
from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import pathlib
import sys
import traceback
import typing

from PyQt6 import QtCore

FORMAT = "[%(levelname)s] %(asctime)s %(name)s: %(message)s"
_fault_file: typing.Optional[typing.TextIO] = None


def log_dir() -> pathlib.Path:
    """Moonraker's log folder on a printer, ./logs anywhere else."""
    moonraker_logs = pathlib.Path.home() / "printer_data" / "logs"
    path = moonraker_logs if moonraker_logs.is_dir() else pathlib.Path("logs")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _qt_message(mode, context, message) -> None:
    logging.getLogger("qt").warning(message)


def setup_logging(level: int = logging.INFO) -> pathlib.Path:
    """Send logs to a rotating file and to stderr (journalctl -u MBindScreen)."""
    global _fault_file
    folder = log_dir()
    logfile = folder / "MBindScreen.log"
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(FORMAT)
    to_file = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    to_file.setFormatter(formatter)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.handlers = [to_file, console]
    _fault_file = open(folder / "MBindScreen_fault.log", "a", encoding="utf-8")
    faulthandler.enable(_fault_file)
    QtCore.qInstallMessageHandler(_qt_message)
    return logfile


def install_crash_handler(
    on_error: typing.Optional[typing.Callable[[str], None]] = None,
) -> None:
    """Log unhandled exceptions instead of letting PyQt abort the process.

    One faulty page must not blank the printer screen. Each distinct error is
    logged in full once and reported to ``on_error`` so it shows on the screen.
    """
    seen: set[tuple] = set()

    def hook(kind, value, tb) -> None:
        where = traceback.extract_tb(tb)[-1][:3] if tb else None
        key = (kind.__name__, str(value), where)
        if key in seen:
            return
        seen.add(key)
        logging.getLogger("crash").error(
            "Unhandled exception\n%s",
            "".join(traceback.format_exception(kind, value, tb)),
        )
        if on_error:
            on_error(f"Erro no ecrã: {kind.__name__}: {value}")

    sys.excepthook = hook
