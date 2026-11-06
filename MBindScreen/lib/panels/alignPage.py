"""Manual X/Y calibration: nozzle camera, aiming mark and fine jog.

The macros in calibracao/xy_manual.cfg run the procedure; this page is only their
screen. It follows Klipper state, so it also opens when the calibration starts in
Mainsail, and it replaces the prompt those macros show.

    _ALIGN_VARS.active = 1   the calibration is running: page visible
    prompt open              the head is at the camera: the user can jog
"""
from __future__ import annotations

from lib.i18n import tr
import logging

from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.cameraView import CameraView, camera_transform
from lib.panels.widgets.dialogs import confirm
from lib.prompts import is_align_prompt
from lib.utils.widgets import ChoiceRow, arrow_button, button, card, label
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)
JOG_STEPS = (0.01, 0.05, 0.1, 0.5, 1)
ZOOM_LEVELS = (1, 2, 4)
DEFAULT_ZOOM_INDEX = 1
WAITING_TEXT = tr("A cabeça está a deslocar-se. Aguarda.")


class AlignPage(QtWidgets.QFrame):
    def __init__(self, printer, api, runner, camera_url, mirror, window) -> None:
        super().__init__(window)
        self.printer, self.api, self.runner = printer, api, runner
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)
        root.addLayout(self._build_camera(camera_url, mirror), 1)
        root.addLayout(self._build_controls())
        printer.updated.connect(self.refresh)
        runner.changed.connect(self.refresh)
        self.hide()

    # --- layout ---------------------------------------------------------
    def _build_camera(self, camera_url: str, mirror: bool) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(6)
        self.title = label("", "cardTitle")
        self.step = label("", "dim")
        self.step.setWordWrap(True)
        self.step.setFixedHeight(34)
        self.camera = CameraView(
            self.api, camera_url, transform=camera_transform(mirror, False, 0)
        )
        self.zooms = ChoiceRow(ZOOM_LEVELS, "x", DEFAULT_ZOOM_INDEX)
        for index, widget in enumerate(self.zooms.buttons):
            widget.clicked.connect(lambda _=False, i=index: self._zoom(i))
        self.camera.set_zoom(ZOOM_LEVELS[DEFAULT_ZOOM_INDEX])
        column.addWidget(self.title)
        column.addWidget(self.step)
        column.addWidget(self.camera, 1)
        column.addWidget(self.zooms)
        return column

    def _build_controls(self) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(8)
        frame, layout = card(10, 6)
        frame.setFixedWidth(270)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        self.jog_buttons = []
        for direction, axis, sign, row, col in (
            ("up", "Y", 1, 0, 1),
            ("left", "X", -1, 1, 0),
            ("right", "X", 1, 1, 2),
            ("down", "Y", -1, 2, 1),
        ):
            widget = arrow_button(
                direction,
                f"{axis}{'+' if sign > 0 else '-'}",
                lambda a=axis, s=sign: self._jog(a, s),
                60,
            )
            grid.addWidget(widget, row, col)
            self.jog_buttons.append(widget)
        self.position = label("", "dim")
        self.position.setStyleSheet("qproperty-alignment: AlignCenter;")
        grid.addWidget(self.position, 1, 1)
        layout.addLayout(grid)
        layout.addWidget(label(tr("Passo (mm)"), "dim"))
        self.steps = ChoiceRow(JOG_STEPS, "", 1)
        layout.addWidget(self.steps)
        column.addWidget(frame)
        self.next = button(tr("Seguinte"), self._next, "accent", 58)
        column.addWidget(self.next)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.cancel = button(tr("Cancelar"), self._cancel, height=52)
        self.stop = button(tr("Parar"), self._emergency, "danger", 52)
        row.addWidget(self.cancel)
        row.addWidget(self.stop)
        column.addLayout(row)
        column.addStretch()
        return column

    # --- actions --------------------------------------------------------
    def _zoom(self, index: int) -> None:
        self.camera.set_zoom(ZOOM_LEVELS[index])

    def _jog(self, axis: str, sign: int) -> None:
        self.api.gcode(gc.align_jog(axis, sign * self.steps.value))

    def _next(self) -> None:
        self.runner.start(tr("Calibração X/Y"), gc.ALIGN_NEXT)

    def _cancel(self) -> None:
        confirm(
            self,
            tr("Cancelar a calibração? O passo atual não é gravado."),
            lambda: self.runner.start(tr("A cancelar a calibração"), gc.ALIGN_CANCEL),
            tr("Cancelar calibração"),
            danger=True,
        )

    def _emergency(self) -> None:
        confirm(
            self,
            tr("Paragem de emergência? Pára tudo de imediato."),
            lambda: self.api.call("printer.emergency_stop"),
            "PARAR",
            danger=True,
        )

    # --- display --------------------------------------------------------
    def refresh(self) -> None:
        printer = self.printer
        self.setVisible(bool(printer.get(machine.ALIGN_VARS, "active", 0)))
        if not self.isVisible():
            return
        prompt = printer.prompt
        ready = prompt is not None and is_align_prompt(prompt)
        tool = 1 if printer.get(machine.ALIGN_VARS, "origin_set", 0) else 0
        self.title.setText(tr("Calibração X/Y manual · T{}", tool))
        self.step.setText(prompt.lines[0] if ready and prompt.lines else WAITING_TEXT)
        self.position.setText(
            f"X {printer.position('x'):.2f}\nY {printer.position('y'):.2f}"
        )
        for widget in (*self.jog_buttons, self.next):
            widget.setEnabled(ready)
        self.cancel.setEnabled(not self.runner.running)
