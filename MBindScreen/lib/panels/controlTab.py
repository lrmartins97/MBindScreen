"""Control: move the axes, choose the active head, lights, UV and fans."""
from __future__ import annotations

import logging
import typing

from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import confirm
from lib.panels.widgets.toolActions import select_tool
from lib.utils.icons import pixmap
from lib.utils.theme import ACCENT
from lib.utils.widgets import (
    ChoiceRow,
    LevelSlider,
    arrow_button,
    button,
    card,
    label,
    set_active,
)
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)
JOG_DISTANCES = (0.1, 1, 10, 50)


class LevelRow(QtWidgets.QWidget):
    """Icon, name, percentage and a slider."""

    def __init__(
        self, icon_name: str, title: str, on_level: typing.Callable[[int], None]
    ) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        picture = label()
        picture.setPixmap(pixmap(icon_name, ACCENT, 26))
        name = label(title, "dim")
        name.setFixedWidth(82)
        self.slider = LevelSlider()
        self.slider.released.connect(on_level)
        self.value = label("0%", "dim")
        self.value.setFixedWidth(38)
        layout.addWidget(picture)
        layout.addWidget(name)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value)

    def show_level(self, fraction: float, enabled: bool) -> None:
        self.slider.set_value(fraction * 100)
        self.slider.setEnabled(enabled)
        self.value.setText(f"{self.slider.value}%")


class ControlTab(QtWidgets.QWidget):
    def __init__(self, printer, api) -> None:
        super().__init__()
        self.printer, self.api = printer, api
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        root.addWidget(self._build_jog(), 5)
        root.addLayout(self._build_side(), 6)
        printer.updated.connect(self.refresh)
        self.refresh()

    # --- layout ---------------------------------------------------------
    def _build_jog(self) -> QtWidgets.QFrame:
        frame, layout = card(12, 8)
        layout.addWidget(label("Mover", "cardTitle"))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        self.jog_buttons = []

        # Seen from the front: X+ moves the head right, Y+ to the back (up on the screen).
        def jog_arrow(direction: str, axis: str, sign: int, row: int, col: int) -> None:
            name = f"{axis.upper()}{'+' if sign > 0 else '-'}"
            widget = arrow_button(direction, name, lambda: self._jog(axis, sign), 64)
            grid.addWidget(widget, row, col)
            self.jog_buttons.append(widget)

        def plate_button(text: str, sign: int, row: int) -> None:
            widget = button(text, lambda: self._jog("z", sign), height=64)
            grid.addWidget(widget, row, 3)
            self.jog_buttons.append(widget)

        jog_arrow("up", "y", 1, 0, 1)
        jog_arrow("left", "x", -1, 1, 0)
        jog_arrow("right", "x", 1, 1, 2)
        jog_arrow("down", "y", -1, 2, 1)
        plate_button("Prato\n▲", -1, 0)
        plate_button("Prato\n▼", 1, 2)
        self.home = button("Home", self._home, "accent", 64)
        grid.addWidget(self.home, 1, 1)
        self.z_label = label("Z", "dim")
        self.z_label.setStyleSheet("qproperty-alignment: AlignCenter;")
        grid.addWidget(self.z_label, 1, 3)
        layout.addLayout(grid)
        self.distances = ChoiceRow(JOG_DISTANCES, "", 1)
        layout.addWidget(label("Distância (mm)", "dim"))
        layout.addWidget(self.distances)
        self.hint = label("", "dim")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addStretch()
        return frame

    def _build_side(self) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(12)
        tools, tools_layout = card(12, 8)
        tools_layout.addWidget(label("Cabeça ativa", "cardTitle"))
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.tool_buttons = {}
        for tool in machine.TOOLS:
            widget = button(f"T{tool}", lambda t=tool: self._select(t), "choice", 58)
            self.tool_buttons[tool] = widget
            row.addWidget(widget)
        tools_layout.addLayout(row)
        self.motors = button("Desligar motores", self._motors_off, height=46)
        tools_layout.addWidget(self.motors)
        column.addWidget(tools)

        outputs, outputs_layout = card(12, 6)
        outputs_layout.addWidget(label("Câmara", "cardTitle"))
        self.light = LevelRow(
            "bulb", "Luz", lambda v: self._set_pin("Led_Chamber", v)
        )
        self.fan = LevelRow(
            "fan", "Ventoinha", lambda v: self._set_fan("Chamber_Fan", v)
        )
        self.uv = LevelRow("uv", "UV", self._set_uv)
        for widget in (self.light, self.fan, self.uv):
            outputs_layout.addWidget(widget)
        column.addWidget(outputs)
        column.addStretch()
        return column

    # --- actions --------------------------------------------------------
    def _jog(self, axis: str, sign: int) -> None:
        low, high = self.printer.axis_limits(axis)
        if axis == "z":
            low = max(low, machine.Z_JOG_MIN)
        wanted = sign * self.distances.value
        distance = machine.clamp_jog(self.printer.position(axis), wanted, low, high)
        if distance == 0:
            self.hint.setText(f"Limite do eixo {axis.upper()} atingido.")
            return
        self.hint.setText("")
        speed = machine.JOG_SPEED_Z if axis == "z" else machine.JOG_SPEED_XY
        self.api.gcode(gc.jog(axis.upper(), distance, speed))

    def _home(self) -> None:
        confirm(
            self,
            "Fazer home a todos os eixos? Sem o home do Z feito, o prato desce 8 mm "
            "em cada home.",
            lambda: self.api.gcode(gc.HOME_ALL),
            "Home",
        )

    def _select(self, tool: int) -> None:
        select_tool(self.printer, self.api, tool)

    def _motors_off(self) -> None:
        self.api.gcode(gc.MOTORS_OFF)

    def _set_pin(self, pin: str, percent: int) -> None:
        self.api.gcode(gc.set_pin(pin, percent / 100))

    def _set_fan(self, fan: str, percent: int) -> None:
        self.api.gcode(gc.set_fan(fan, percent / 100))

    def _set_uv(self, percent: int) -> None:
        if percent == 0:
            self._set_pin("UV", 0)
            return
        scrim = confirm(
            self,
            f"Ligar os LED UV a {percent}%? Não olhar diretamente para a luz.",
            lambda: self._set_pin("UV", percent),
            "Ligar UV",
            danger=True,
        )
        scrim.destroyed.connect(self.refresh)

    # --- display --------------------------------------------------------
    def refresh(self) -> None:
        printer = self.printer
        idle = printer.can_act
        homed = printer.homed()
        for widget in self.jog_buttons:
            widget.setEnabled(idle and homed)
        self.home.setEnabled(idle)
        self.motors.setEnabled(idle)
        active = printer.active_tool
        for tool, widget in self.tool_buttons.items():
            set_active(widget, tool == active)
            widget.setEnabled(idle)  # without home it only picks the plunger
        if homed:
            self.z_label.setText(
                f"X {printer.position('x'):.1f}\nY {printer.position('y'):.1f}\n"
                f"Z {printer.position('z'):.2f}"
            )
        else:
            self.z_label.setText("Sem\nhome")
        ready = printer.ready
        self.light.show_level(printer.get(machine.CHAMBER_LIGHT, "value", 0) or 0, ready)
        self.fan.show_level(printer.get(machine.CHAMBER_FAN, "speed", 0) or 0, ready)
        self.uv.show_level(printer.get(machine.UV_PIN, "value", 0) or 0, ready)
