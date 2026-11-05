"""Syringes (the filament tab of the M-BIND): heat, move the plunger, choose the
paste and clean the nozzle, for each of the two heads."""
from __future__ import annotations

from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import choose, confirm, numpad
from lib.utils.widgets import (
    ChoiceRow,
    HoldArea,
    button,
    card,
    label,
    set_card_active,
    status_chip,
)
from PyQt6 import QtWidgets

DISTANCES = (0.1, 0.5, 1, 5)  # mm of plunger travel
SPEEDS = (0.1, 0.2, 0.5, 1)  # mm/s of plunger travel


class SyringePanel(HoldArea):
    """A touch on the card selects this head; holding it sets the temperature."""

    def __init__(self, tool: int, tab: "SyringeTab") -> None:
        super().__init__("card")
        self.tool_index, self.tab = tool, tab
        self.clicked.connect(self._select)
        self.held.connect(self._edit_temperature)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(label(f"Seringa T{tool}", "cardTitle"))
        top.addStretch()
        self.chip = status_chip("Ativa")
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
        layout.addWidget(label("Manter premido: temperatura", "dim"))

        self.material = button("—", self._pick_material, height=44)
        layout.addWidget(self.material)
        moves = QtWidgets.QHBoxLayout()
        moves.setSpacing(8)
        self.retract = button("Recuar", lambda: self._move(-1), height=56)
        self.advance = button("Avançar", lambda: self._move(1), "accent", 56)
        moves.addWidget(self.retract)
        moves.addWidget(self.advance)
        layout.addLayout(moves)
        self.clean = button("Limpar bico", self._clean, height=44)
        layout.addWidget(self.clean)

    def _select(self) -> None:
        printer = self.tab.printer
        if printer.can_act and self.tool_index != printer.active_tool:
            self.tab.api.gcode(gc.select_tool(self.tool_index))

    def _edit_temperature(self) -> None:
        printer = self.tab.printer
        if not printer.ready:
            return
        numpad(
            self,
            f"Temperatura T{self.tool_index}",
            printer.tool(self.tool_index).target,
            printer.max_temp(self.tool_index),
            lambda value: self.tab.api.gcode(gc.set_temperature(self.tool_index, value)),
        )

    def _pick_material(self) -> None:
        options = [("Sem material", 0)]
        options += [(name, slot) for slot, name in self.tab.printer.materials()]
        choose(
            self,
            f"Material da seringa T{self.tool_index}",
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
            f"Limpar o bico do T{self.tool_index}? A cabeça desloca-se para as estações "
            "de limpeza (faz home se for preciso).",
            lambda: self.tab.runner.start(
                f"Limpar bico T{self.tool_index}", gc.clean_nozzle(self.tool_index)
            ),
            "Limpar",
        )

    def refresh(self) -> None:
        printer = self.tab.printer
        tool = printer.tool(self.tool_index)
        set_card_active(self, tool.active)
        self.chip.setVisible(tool.active)
        self.temperature.setText(f"{tool.temperature:.1f} °C")
        self.target.setText(f"alvo {tool.target:.0f} °C" if tool.target else "desligada")
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
        grid.addWidget(label("Quanto o êmbolo anda (mm)", "dim"), 0, 0)
        grid.addWidget(label("Velocidade do êmbolo (mm/s)", "dim"), 0, 1)
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
            f"O êmbolo empurra {machine.format_volume(volume)} a "
            f"{machine.format_volume(flow)}/s (seringa de {diameter:g} mm)"
        )
