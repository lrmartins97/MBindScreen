"""Syringes (the filament tab of the M-BIND): heat, move the plunger, choose the
paste and clean the nozzle, for each of the two heads."""
from __future__ import annotations

from lib.i18n import tr
from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import choose, confirm
from lib.panels.widgets.toolActions import edit_temperature, select_tool
from lib.utils.widgets import (
    ChoiceRow,
    HoldArea,
    button,
    card,
    label,
    set_card_active,
    status_chip,
)
from PyQt6 import QtCore, QtWidgets

DISTANCES = (0.1, 0.5, 1, 5)  # mm of plunger travel
SPEEDS = (0.1, 0.2, 0.5, 1)  # mm/s of plunger travel


class SyringePanel(HoldArea):
    """A touch on the card selects this head. Touching the temperature, or holding the
    card anywhere, also opens the temperature of this head."""

    def __init__(self, tool: int, tab: "SyringeTab") -> None:
        super().__init__("card")
        self.tool_index, self.tab = tool, tab
        self._pressed_at = QtCore.QPoint()
        self.clicked.connect(self._on_touch)
        self.held.connect(self._edit_temperature)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(label(tr("Seringa T{}", tool), "cardTitle"))
        top.addStretch()
        self.chip = status_chip(tr("Ativa"))
        top.addWidget(self.chip)
        layout.addLayout(top)

        self.temp_area = QtWidgets.QFrame()
        self.temp_area.setObjectName("cell")
        temp_layout = QtWidgets.QHBoxLayout(self.temp_area)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        self.temperature = label("—", "big")
        self.target = label("", "dim")
        temp_layout.addWidget(self.temperature)
        temp_layout.addStretch()
        temp_layout.addWidget(self.target)
        layout.addWidget(self.temp_area)
        layout.addWidget(label(tr("Toca na temperatura para a mudar"), "dim"))

        self.material = button("—", self._pick_material, height=44)
        layout.addWidget(self.material)
        moves = QtWidgets.QHBoxLayout()
        moves.setSpacing(8)
        self.retract = button(tr("Recuar"), lambda: self._move(-1), height=56)
        self.advance = button(tr("Avançar"), lambda: self._move(1), "accent", 56)
        moves.addWidget(self.retract)
        moves.addWidget(self.advance)
        layout.addLayout(moves)
        self.clean = button(tr("Limpar bico"), self._clean, height=44)
        layout.addWidget(self.clean)

    def mousePressEvent(self, event) -> None:
        self._pressed_at = event.position().toPoint()
        super().mousePressEvent(event)

    def _on_touch(self) -> None:
        if self.temp_area.geometry().contains(self._pressed_at):
            self._edit_temperature()
        else:
            self._select()

    def _select(self) -> None:
        select_tool(self.tab.printer, self.tab.api, self.tool_index)

    def _edit_temperature(self) -> None:
        edit_temperature(self, self.tab.printer, self.tab.api, self.tool_index)

    def _pick_material(self) -> None:
        options = [(tr("Sem material"), 0)]
        options += [(name, slot) for slot, name in self.tab.printer.materials()]
        choose(
            self,
            tr("Material da seringa T{}", self.tool_index),
            options,
            lambda slot: self.tab.api.gcode(gc.set_material(self.tool_index, slot)),
        )

    def _move(self, sign: int) -> None:
        self.tab.api.gcode(
            gc.move_plunger(
                self.tool_index,
                sign * self.tab.distance.value,
                self.tab.speed.value,
            )
        )

    def _clean(self) -> None:
        confirm(
            self,
            tr("Limpar o bico do T{}? A cabeça desloca-se para as estações de limpeza (faz home se for preciso).", self.tool_index),
            lambda: self.tab.runner.start(
                tr("Limpar bico T{}", self.tool_index), gc.clean_nozzle(self.tool_index)
            ),
            tr("Limpar"),
        )

    def refresh(self) -> None:
        printer = self.tab.printer
        tool = printer.tool(self.tool_index)
        set_card_active(self, tool.active)
        self.chip.setVisible(tool.active)
        self.temperature.setText(f"{tool.temperature:.1f} °C")
        self.target.setText(tr("alvo {:.0f} °C", tool.target) if tool.target else tr("desligada"))
        self.material.setText(tool.material)
        idle = printer.can_act
        for widget in (self.retract, self.advance, self.clean, self.material):
            widget.setEnabled(idle)


class SyringeTab(QtWidgets.QWidget):
    def __init__(self, printer, api, runner) -> None:
        super().__init__()
        self.printer, self.api, self.runner = printer, api, runner
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        self.panels = [SyringePanel(tool, self) for tool in machine.TOOLS]
        for panel in self.panels:
            row.addWidget(panel, 1)
        root.addLayout(row, 1)

        settings, layout = card(12, 6)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        self.distance = ChoiceRow(DISTANCES, "", 1)
        self.speed = ChoiceRow(SPEEDS, "", 2)
        grid.addWidget(label(tr("Quanto o êmbolo anda (mm)"), "dim"), 0, 0)
        grid.addWidget(label(tr("Velocidade do êmbolo (mm/s)"), "dim"), 0, 1)
        grid.addWidget(self.distance, 1, 0)
        grid.addWidget(self.speed, 1, 1)
        layout.addLayout(grid)
        self.equivalent = label("", "dim")
        layout.addWidget(self.equivalent)
        root.addWidget(settings)
        for choice in (self.distance, self.speed):
            for widget in choice.buttons:
                widget.clicked.connect(lambda _=False: self.refresh())
        printer.updated.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        for panel in self.panels:
            panel.refresh()
        diameter = self.printer.syringe_diameter(0)
        volume = machine.plunger_volume(self.distance.value, diameter)
        flow = machine.plunger_volume(self.speed.value, diameter)
        self.equivalent.setText(
            tr("O êmbolo empurra {} a {}/s (seringa de {:g} mm)", machine.format_volume(volume), machine.format_volume(flow), diameter)
        )
