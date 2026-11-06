"""Print page: progress, PRINT_START stages, temperatures, live Z, pause and cancel."""
from __future__ import annotations

from lib.i18n import tr
import logging

from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import confirm, numpad
from lib.utils.theme import ACCENT, DIM, GREEN, RED
from lib.utils.widgets import (
    ChoiceRow,
    Clickable,
    Ring,
    button,
    card,
    label,
    set_card_active,
)
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
Z_STEPS = (0.01, 0.05)
Z_LIMIT = 1.0  # mm of change from the screen, on top of the start of the print


class StageBar(QtWidgets.QWidget):
    """The PRINT_START stages as a row of words; the current one is highlighted."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.labels = [label(tr(title), "dim") for _, title in machine.PREPARE_STAGES]
        for widget in self.labels:
            layout.addWidget(widget)
        layout.addStretch()

    def set_stage(self, stage: int) -> None:
        for index, widget in enumerate(self.labels):
            color = ACCENT if index == stage else GREEN if index < stage else DIM
            weight = 600 if index == stage else 400
            widget.setStyleSheet(f"color: {color}; font-weight: {weight};")


class TempCard(Clickable):
    def __init__(self, tool: int) -> None:
        super().__init__("card")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(0)
        self.title = label(f"T{tool}", "dim")
        self.value = label("—", "value")
        self.material = label("", "dim")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.material)
        layout.addStretch()


class PrintTab(QtWidgets.QWidget):
    finished = QtCore.pyqtSignal(name="finished")

    def __init__(self, printer, api) -> None:
        super().__init__()
        self.printer, self.api = printer, api
        self.meta: dict = {}
        self._filename = ""
        self._z_start = 0.0
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 12)
        root.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(14)
        self.ring = Ring()
        info, info_layout = card(14, 2)
        self.name = label("—", "cardTitle")
        self.name.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.status = label("", "dim")
        self.stages = StageBar()
        info_layout.addWidget(self.name)
        info_layout.addWidget(self.status)
        info_layout.addWidget(self.stages)
        info_layout.addSpacing(4)
        values = QtWidgets.QGridLayout()
        values.setHorizontalSpacing(20)
        self.values = {}
        for column, (key, title) in enumerate(
            (("layer", tr("Camada")), ("elapsed", tr("Decorrido")), ("remaining", tr("Restante")))
        ):
            value = label("—", "value")
            values.addWidget(label(title, "dim"), 0, column)
            values.addWidget(value, 1, column)
            self.values[key] = value
        info_layout.addLayout(values)
        info_layout.addStretch()
        top.addWidget(self.ring, 2)
        top.addWidget(info, 4)
        root.addLayout(top, 3)

        middle = QtWidgets.QHBoxLayout()
        middle.setSpacing(10)
        self.temps = {tool: TempCard(tool) for tool in machine.TOOLS}
        for tool, temp_card in self.temps.items():
            temp_card.clicked.connect(lambda t=tool: self._edit_temperature(t))
            middle.addWidget(temp_card, 2)
        z_card, z_layout = card(10, 4)
        z_row = QtWidgets.QHBoxLayout()
        z_row.setSpacing(6)
        self.z_value = label("Z", "dim")
        self.z_down = button("−", lambda: self._babystep(-1), height=44)
        self.z_up = button("+", lambda: self._babystep(1), height=44)
        self.z_steps = ChoiceRow(Z_STEPS)
        z_row.addWidget(self.z_down, 1)
        z_row.addWidget(self.z_steps, 2)
        z_row.addWidget(self.z_up, 1)
        z_layout.addWidget(self.z_value)
        z_layout.addLayout(z_row)
        z_layout.addStretch()
        middle.addWidget(z_card, 5)
        root.addLayout(middle, 2)

        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(12)
        self.pause = button(tr("Pausa"), self._pause, height=56)
        self.cancel = button(tr("Cancelar impressão"), self._cancel, "danger", 56)
        self.done = button(tr("Concluir"), self.finished.emit, "accent", 56)
        for widget in (self.pause, self.cancel, self.done):
            bottom.addWidget(widget)
        root.addLayout(bottom)
        printer.updated.connect(self.refresh)
        self.refresh()

    # --- actions --------------------------------------------------------
    def _edit_temperature(self, tool: int) -> None:
        printer = self.printer
        if printer.is_printing and printer.ready:
            numpad(
                self,
                tr("Temperatura T{}", tool),
                printer.tool(tool).target,
                printer.max_temp(tool),
                lambda value: self.api.gcode(gc.set_temperature(tool, value)),
            )

    def _babystep(self, sign: int) -> None:
        delta = sign * self.z_steps.value
        change = self.printer.z_offset + delta - self._z_start
        if abs(change) > Z_LIMIT + 1e-9:
            self.status.setText(tr("Limite do ajuste de Z atingido (±{:g} mm)", Z_LIMIT))
            return
        self.api.gcode(gc.babystep(delta))

    def _pause(self) -> None:
        paused = self.printer.print_state == "paused"
        self.api.call("printer.print.resume" if paused else "printer.print.pause")

    def _cancel(self) -> None:
        confirm(
            self,
            tr("Cancelar a impressão? Não pode ser retomada."),
            lambda: self.api.call("printer.print.cancel"),
            tr("Cancelar impressão"),
            danger=True,
        )

    def _on_metadata(self, result, _error) -> None:
        if result:
            self.meta = result
            self.refresh()

    # --- display --------------------------------------------------------
    def _layer_text(self) -> str:
        info = self.printer.get("print_stats", "info", None) or {}
        current = info.get("current_layer")
        total = info.get("total_layer") or self.meta.get("layer_count")
        if not current:
            return "—"
        return f"{current} / {total}" if total else f"{current}"

    def refresh(self) -> None:
        printer = self.printer
        state = printer.print_state
        active = printer.is_printing
        finished = state in ("complete", "cancelled", "error")
        full = printer.get("print_stats", "filename", "") or ""
        if full != self._filename:
            self._filename, self.meta = full, {}
            self._z_start = printer.z_offset
            if full:
                self.api.call(
                    "server.files.metadata", {"filename": full}, self._on_metadata
                )
        progress = 1.0 if state == "complete" else (
            printer.get("virtual_sdcard", "progress", 0) or 0
        )
        elapsed = printer.get("print_stats", "print_duration", 0) or 0
        title = tr(machine.PRINT_STATE_TITLES.get(state, state.title()))
        message = printer.get("display_status", "message", "") or ""
        stage = machine.prepare_stage(message) if active else -1
        caption = tr("A preparar") if stage >= 0 else title
        color = RED if state == "error" else ACCENT
        self.ring.set(progress, f"{progress * 100:.0f}%", caption, color)
        self.name.setText(full.rsplit("/", 1)[-1] or tr("Sem impressão"))

        self.stages.setVisible(stage >= 0)
        if stage >= 0:
            self.stages.set_stage(stage)
        error = printer.get("print_stats", "message", "") if state == "error" else ""
        self.status.setText(error or (message if stage >= 0 else title))

        remaining = 0 if state == "complete" else machine.remaining_time(
            progress, elapsed, self.meta.get("estimated_time")
        )
        show = active or finished
        self.values["layer"].setText(self._layer_text() if show else "—")
        self.values["elapsed"].setText(machine.format_time(elapsed) if show else "—")
        self.values["remaining"].setText(machine.format_time(remaining) if show else "—")

        for index, temp_card in self.temps.items():
            tool = printer.tool(index)
            set_card_active(temp_card, tool.active)
            temp_card.value.setText(f"{tool.temperature:.1f} / {tool.target:.0f} °C")
            temp_card.material.setText(tool.material)
        self.z_value.setText(tr("Ajuste de Z: {:+.3f} mm", printer.z_offset))
        can_adjust = active and printer.ready and printer.homed("z")
        for widget in (self.z_down, self.z_up):
            widget.setEnabled(can_adjust)
        self.pause.setText(tr("Retomar") if state == "paused" else tr("Pausa"))
        for widget in (self.pause, self.cancel):
            widget.setVisible(active)
            widget.setEnabled(printer.ready)
        self.done.setVisible(not active)
