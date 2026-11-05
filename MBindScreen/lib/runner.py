"""Runs a long G-code routine and blocks the UI with a status box meanwhile.

Calibrations take minutes and Moonraker answers only at the end, so the box shows
the latest console line as progress and always offers the emergency stop.
"""
from __future__ import annotations

import logging

from lib.utils.theme import ACCENT, RED
from lib.utils.widgets import CENTER, Clickable, PopupBox, button, label
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
STARTING = "A começar…"


class Runner(QtCore.QObject):
    changed = QtCore.pyqtSignal(name="changed")
    # The answer to a script can arrive before the status update that says Klipper
    # now waits for the user (updates come every 250 ms), so wait for it to settle.
    SETTLE_MS = 400

    def __init__(self, api, printer, parent=None) -> None:
        super().__init__(parent)
        self.api, self.printer = api, printer
        self.title = ""
        self.message = ""
        self.running = False
        self.finished = False
        self.ok = True
        printer.console_line.connect(self._on_console)

    def start(self, title: str, script: str) -> None:
        if self.running:
            return
        logger.info("Routine: %s", title)
        self.title, self.message = title, STARTING
        self.running, self.finished, self.ok = True, False, True
        self.changed.emit()
        self.api.gcode(script, self._result)

    def _on_console(self, line: str) -> None:
        if self.running and not line.startswith("!!"):
            self.message = line.removeprefix("//").strip()
            self.changed.emit()

    def _result(self, _result, error) -> None:
        if error:
            text = error.get("message", "Falhou") if isinstance(error, dict) else str(error)
            logger.warning("Routine failed: %s", text)
            self.running, self.ok, self.message, self.finished = False, False, text, True
            self.changed.emit()
        elif self.SETTLE_MS:
            QtCore.QTimer.singleShot(self.SETTLE_MS, self._succeeded)
        else:
            self._succeeded()

    def _succeeded(self) -> None:
        # An interactive step (paper test, screws, camera) continues on its own page.
        self.running = False
        self.finished = not self._waiting_for_user()
        self.ok = True
        if self.message == STARTING:  # otherwise keep the last line from the macro
            self.message = "Sem mensagens da máquina."
        self.changed.emit()

    def _waiting_for_user(self) -> bool:
        return bool(
            self.printer.get("manual_probe", "is_active", False)
            or self.printer.get("bed_screws", "is_active", False)
            or self.printer.prompt is not None
        )

    def acknowledge(self) -> None:
        self.finished = False
        self.changed.emit()

    def emergency_stop(self) -> None:
        logger.warning("Emergency stop from a routine")
        self.api.call("printer.emergency_stop")


class RunOverlay(Clickable):
    """Status box of the routine in progress, then its result."""

    def __init__(self, runner: Runner, window: QtWidgets.QWidget) -> None:
        super().__init__("scrim")
        self.setParent(window)
        self.runner = runner
        self.box = PopupBox(500)
        layout = QtWidgets.QVBoxLayout(self.box)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        self.title = label("", "cardTitle")
        self.text = label()
        self.text.setWordWrap(True)
        self.stop = button("Paragem de emergência", runner.emergency_stop, "danger", 54)
        self.ok = button("OK", runner.acknowledge, "accent", 54)
        for widget in (self.title, self.text, self.stop, self.ok):
            layout.addWidget(widget)
        outer = QtWidgets.QVBoxLayout(self)
        outer.addStretch()
        outer.addWidget(self.box, alignment=CENTER)
        outer.addStretch()
        runner.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        runner = self.runner
        self.setVisible(runner.running or runner.finished)
        if not self.isVisible():
            return
        self.raise_()
        if runner.running:
            self.title.setText(runner.title)
            self.title.setStyleSheet("")
        else:
            self.title.setText("Concluído" if runner.ok else "Falhou")
            self.title.setStyleSheet(f"color: {ACCENT if runner.ok else RED};")
        self.text.setText(runner.message)
        self.stop.setVisible(runner.running)
        self.ok.setVisible(runner.finished)
        self.box.fit()
