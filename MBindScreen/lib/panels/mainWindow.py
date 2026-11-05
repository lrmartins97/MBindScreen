"""Main window: creates the subsystems and connects them. No logic of its own."""
from __future__ import annotations

import logging
import time

from lib.moonrakerComm import MoonWebSocket
from lib.panels.alignPage import AlignPage
from lib.panels.calibrationTab import CalibrationTab
from lib.panels.controlTab import ControlTab
from lib.panels.filesPage import FilesPage
from lib.panels.homeTab import HomeTab
from lib.panels.printTab import PrintTab
from lib.panels.settingsTab import SettingsTab
from lib.panels.syringeTab import SyringeTab
from lib.panels.widgets.adjustOverlay import AdjustOverlay
from lib.panels.widgets.connectionOverlay import ConnectionOverlay
from lib.panels.widgets.dialogs import confirm
from lib.panels.widgets.promptDialog import PromptDialog
from lib.printer import Printer
from lib.runner import RunOverlay, Runner
from lib.utils.widgets import NavBar
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
TABS = ("home", "controls", "syringe", "calibrate", "settings")
HOME, CONTROL, SYRINGES, CALIBRATION, SETTINGS = range(5)
RESTART_DELAY_MS = 1000
ACTIVITY = (
    QtCore.QEvent.Type.MouseButtonPress,
    QtCore.QEvent.Type.TouchBegin,
    QtCore.QEvent.Type.KeyPress,
)


class SleepCover(QtWidgets.QFrame):
    """Black layer; the touch that wakes the screen presses nothing underneath."""

    def __init__(self, window: QtWidgets.QWidget) -> None:
        super().__init__(window)
        self.setObjectName("sleep")
        self.hide()

    def mousePressEvent(self, _event) -> None:
        self.hide()


class MainWindow(QtWidgets.QWidget):
    def __init__(self, config, api=None, read_only: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("MBindScreen")
        self.config = config
        self.printer = Printer(self)
        self.api = api or MoonWebSocket(config.host, config.port, self, read_only)
        self.printer.connect_to(self.api)
        self.runner = Runner(self.api, self.printer, self)
        self._print_was_active = False
        self._last_touch = time.monotonic()

        self.nav = NavBar(TABS)
        self.home = HomeTab(self.printer)
        self.control = ControlTab(self.printer, self.api)
        self.syringes = SyringeTab(self.printer, self.api, self.runner)
        self.calibration = CalibrationTab(self.printer, self.api, self.runner)
        self.settings = SettingsTab(self.printer, self.api)
        self.printing = PrintTab(self.printer, self.api)
        self.files = FilesPage(self.printer, self.api, lambda: self.goto(HOME))
        self.stack = QtWidgets.QStackedWidget()
        for page in (
            self.home,
            self.control,
            self.syringes,
            self.calibration,
            self.settings,
            self.printing,
            self.files,
        ):
            self.stack.addWidget(page)
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.nav)
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(0)
        if read_only:
            trial = QtWidgets.QLabel("Modo de experiência: os comandos não chegam à máquina")
            trial.setObjectName("trial")
            right.addWidget(trial)
        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)

        # Created first so that everything else (the routine box above all) stays on top.
        self.align = AlignPage(
            self.printer,
            self.api,
            self.runner,
            self.api.camera_url(config.calibration_camera),
            self,
        )
        self.overlays = [
            ConnectionOverlay(self.printer, self.api, self),
            AdjustOverlay(self.printer, self.api, self),
            PromptDialog(self.printer, self.api, self),
            RunOverlay(self.runner, self),
            self.align,
        ]
        self.sleep_cover = SleepCover(self)
        self._connect_signals()
        self._start_sleep_timer()
        self.refresh()
        self.api.open()

    def _connect_signals(self) -> None:
        self.nav.selected.connect(self.goto)
        self.nav.emergency.connect(self.emergency_stop)
        self.home.open_files.connect(self.open_files)
        self.home.open_syringes.connect(lambda: self.goto(SYRINGES))
        self.printing.finished.connect(lambda: self.goto(HOME))
        self.printer.updated.connect(self.refresh)
        self.api.self_updated.connect(self._restart_after_update)

    def _restart_after_update(self) -> None:
        """Moonraker does not restart this service: if it did, updating while
        KlipperScreen is on screen would swap the screen. Exiting here restarts
        the app (Restart=always) only when it was the one running."""
        logger.info("Exiting to load the new version")
        QtCore.QTimer.singleShot(RESTART_DELAY_MS, QtWidgets.QApplication.instance().quit)

    def _start_sleep_timer(self) -> None:
        QtWidgets.QApplication.instance().installEventFilter(self)
        timer = QtCore.QTimer(self)
        timer.setInterval(5000)
        timer.timeout.connect(self._check_sleep)
        timer.start()

    def eventFilter(self, _obj, event) -> bool:
        if event.type() in ACTIVITY:
            self._last_touch = time.monotonic()
        return False

    def _check_sleep(self) -> None:
        minutes = self.config.sleep_minutes
        if minutes and time.monotonic() - self._last_touch > minutes * 60:
            self.sleep_cover.setGeometry(self.rect())
            self.sleep_cover.show()
            self.sleep_cover.raise_()

    def resizeEvent(self, event) -> None:
        for overlay in self.overlays:
            overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    # --- navigation -----------------------------------------------------
    def goto(self, index: int) -> None:
        page = self.stack.widget(index)
        if hasattr(page, "reset"):
            page.reset()  # a tab always opens on its first page
        self.nav.set_current(index if index <= SETTINGS else HOME)
        self.stack.setCurrentIndex(index)

    def open_files(self) -> None:
        if self.printer.is_printing:
            self.stack.setCurrentWidget(self.printing)
        else:
            self.stack.setCurrentWidget(self.files)
        self.nav.set_current(HOME)

    def emergency_stop(self) -> None:
        confirm(
            self,
            "Paragem de emergência? Pára tudo de imediato. Depois é preciso reiniciar "
            "o firmware.",
            lambda: self.api.call("printer.emergency_stop"),
            "PARAR",
            danger=True,
        )

    def refresh(self) -> None:
        self.nav.set_alerts(len(self.printer.alerts))
        active = self.printer.is_printing
        if active and not self._print_was_active:
            logger.info("Print started: showing the print page")
            self.stack.setCurrentWidget(self.printing)
            self.nav.set_current(HOME)
        self._print_was_active = active
