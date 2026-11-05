"""Runs the real window against the simulator, without a display."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from configfile import ScreenConfig  # noqa: E402
from lib.panels.mainWindow import MainWindow  # noqa: E402
from lib.runner import Runner  # noqa: E402
from lib.simulator import SimulatedPrinter  # noqa: E402
from lib.utils.theme import QSS  # noqa: E402


@pytest.fixture
def api():
    return SimulatedPrinter(speed=1.0)


@pytest.fixture
def window(qtbot, qapp, api, monkeypatch):
    monkeypatch.setattr(Runner, "SETTLE_MS", 0)  # the simulator answers in order
    qapp.setStyleSheet(QSS)
    win = MainWindow(ScreenConfig(), api)
    qtbot.addWidget(win)
    win.setFixedSize(800, 480)
    win.show()
    qtbot.waitUntil(lambda: win.printer.ready, timeout=2000)
    return win


def top_dialog(window):
    """The modal box currently open."""
    from lib.panels.widgets.dialogs import Scrim

    return [s for s in window.findChildren(Scrim) if s.isVisible()][-1]


def click_button(root, text):
    """Press the visible button with this text, as a finger would."""
    from PyQt6 import QtCore, QtWidgets

    for widget in root.findChildren(QtWidgets.QPushButton):
        if widget.text() == text and widget.isVisible() and widget.isEnabled():
            widget.click()
            QtCore.QCoreApplication.processEvents()
            return widget
    raise AssertionError(f"No enabled visible button {text!r}")
