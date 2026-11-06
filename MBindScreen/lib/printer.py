"""Printer: single source of truth for the machine state.

Panels connect to ``updated`` and read through ``get`` or the helpers below;
they never parse Moonraker messages themselves.
"""
from __future__ import annotations

from lib.i18n import tr
import collections
import dataclasses
import logging
import math
import time
import typing

from lib import machine
from lib.prompts import Prompt, PromptParser
from PyQt6 import QtCore

logger = logging.getLogger(__name__)
MAX_CONSOLE_LINES = 200
MAX_ALERTS = 50


@dataclasses.dataclass(frozen=True)
class ToolView:
    index: int
    temperature: float
    target: float
    active: bool
    material_slot: int
    material: str


def _merge(target: dict, update: dict) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


class Printer(QtCore.QObject):
    updated = QtCore.pyqtSignal(name="updated")
    console_line = QtCore.pyqtSignal(str, name="console-line")
    prompt_show = QtCore.pyqtSignal(object, name="prompt-show")
    prompt_close = QtCore.pyqtSignal(name="prompt-close")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.data: dict[str, dict] = {}
        self.link = False
        self.klippy = "disconnected"
        self.klippy_message = ""
        self.objects: list[str] = []
        self.settings: dict = {}
        self.console: collections.deque[tuple[float, str]] = collections.deque(
            maxlen=MAX_CONSOLE_LINES
        )
        self.alerts: collections.deque[tuple[float, str]] = collections.deque(
            maxlen=MAX_ALERTS
        )
        self._prompts = PromptParser()
        self.prompt: typing.Optional[Prompt] = None  # the prompt open right now

    def connect_to(self, api) -> None:
        api.link_up.connect(lambda: self._set_link(True))
        api.link_down.connect(lambda: self._set_link(False))
        api.klippy.connect(self._set_klippy)
        api.objects.connect(self._set_objects)
        api.settings.connect(self._set_settings)
        api.status.connect(self.apply)
        api.gcode_response.connect(self.add_console_line)

    # --- incoming -------------------------------------------------------
    def apply(self, status: dict) -> None:
        _merge(self.data, status)
        webhooks = status.get("webhooks")
        if webhooks and "state" in webhooks:
            self.klippy = webhooks["state"]
            self.klippy_message = webhooks.get("state_message", self.klippy_message)
        self.updated.emit()

    def _set_link(self, up: bool) -> None:
        logger.info("Moonraker link: %s", "up" if up else "down")
        self.link = up
        if not up:
            self.klippy = "disconnected"
            self.prompt = None
        self.updated.emit()

    def _set_klippy(self, state: str, message: str) -> None:
        if state != self.klippy:
            logger.info("Klippy state: %s %s", state, message)
        self.klippy, self.klippy_message = state, message
        self.updated.emit()

    def _set_objects(self, names: list) -> None:
        self.objects = list(names)
        logger.info("Klipper objects: %d", len(names))
        self.updated.emit()

    def _set_settings(self, settings: dict) -> None:
        self.settings = settings
        self.updated.emit()

    def add_console_line(self, line: str) -> None:
        action = self._prompts.feed(line)
        if action == "show":
            self.prompt = self._prompts.prompt
            self.prompt_show.emit(self.prompt)
            self.updated.emit()
            return
        if action == "close":
            self.prompt = None
            self.prompt_close.emit()
            self.updated.emit()
            return
        if "action:prompt_" in line:
            return
        self.console.append((time.time(), line))
        if line.startswith("!!"):
            self.add_alert(line.lstrip("! ").strip())
        self.console_line.emit(line)

    def add_alert(self, text: str) -> None:
        logger.warning("Alert: %s", text)
        self.alerts.append((time.time(), text))
        self.updated.emit()

    def clear_alerts(self) -> None:
        self.alerts.clear()
        self.updated.emit()

    # --- reading --------------------------------------------------------
    def get(self, obj: str, key: str, default: typing.Any = None) -> typing.Any:
        return self.data.get(obj, {}).get(key, default)

    @property
    def ready(self) -> bool:
        return self.link and self.klippy == "ready"

    @property
    def print_state(self) -> str:
        return self.get("print_stats", "state", "standby") or "standby"

    @property
    def is_printing(self) -> bool:
        return self.print_state in machine.ACTIVE_PRINT_STATES

    @property
    def can_act(self) -> bool:
        """Manual actions: connected and no print running."""
        return self.ready and not self.is_printing

    @property
    def active_tool(self) -> int:
        """Same rule as the macros: dual_carriage decides, else the extruder. Without
        home a head is chosen with SERINGA_Tn, which only changes the extruder."""
        carriages = self.data.get("dual_carriage", {})
        if self.homed():
            if carriages.get("carriage_1") == "PRIMARY":
                return 1
            if carriages.get("carriage_0") == "PRIMARY":
                return 0
        return 1 if self.get("toolhead", "extruder") == "extruder1" else 0

    def homed(self, axes: str = "xyz") -> bool:
        homed_axes = self.get("toolhead", "homed_axes", "") or ""
        return all(axis in homed_axes for axis in axes)

    def tool(self, index: int) -> ToolView:
        name = machine.EXTRUDERS[index]
        slot = self.material_slot(index)
        return ToolView(
            index=index,
            temperature=self.get(name, "temperature", 0.0) or 0.0,
            target=self.get(name, "target", 0.0) or 0.0,
            active=self.active_tool == index,
            material_slot=slot,
            material=self.material_name(slot),
        )

    def material_slot(self, tool: int) -> int:
        variables = self.get("save_variables", "variables", {}) or {}
        return int(variables.get(f"tool_{tool}_material", 0) or 0)

    def material_name(self, slot: int) -> str:
        if slot <= 0:
            return tr("Sem material")
        name = self.get(f"{machine.MATERIAL_PREFIX}{slot}", "name", None)
        return str(name) if name else tr("Material {}", slot)

    def materials(self) -> list[tuple[int, str]]:
        return [
            (slot, self.material_name(slot))
            for slot in machine.material_slots(self.objects)
        ]

    def max_temp(self, tool: int) -> float:
        section = self.settings.get(machine.EXTRUDERS[tool], {})
        return float(section.get("max_temp", machine.DEFAULT_MAX_TEMP))

    def syringe_diameter(self, tool: int) -> float:
        section = self.settings.get(machine.EXTRUDERS[tool], {})
        return float(section.get("filament_diameter", machine.DEFAULT_SYRINGE_DIAMETER))

    @property
    def max_plunger_mm(self) -> float:
        value = self.get(machine.SERINGA_VARS, "max_mm", machine.DEFAULT_MAX_PLUNGER_MM)
        return float(value)

    def position(self, axis: str) -> float:
        values = self.get("toolhead", "position", None) or [0, 0, 0, 0]
        return float(values["xyz".index(axis)])

    def axis_limits(self, axis: str) -> tuple[float, float]:
        """Klipper's status keeps the limits of the first carriage, also with T1 active."""
        if axis == "x" and self.data.get("dual_carriage", {}).get("carriage_1") == "PRIMARY":
            section = self.settings.get("dual_carriage", {})
            return (
                float(section.get("position_min", -math.inf)),
                float(section.get("position_max", math.inf)),
            )
        index = "xyz".index(axis)
        low = self.get("toolhead", "axis_minimum", None) or [0, 0, 0, 0]
        high = self.get("toolhead", "axis_maximum", None) or [0, 0, 0, 0]
        return float(low[index]), float(high[index])

    @property
    def z_offset(self) -> float:
        origin = self.get("gcode_move", "homing_origin", None) or [0, 0, 0, 0]
        return float(origin[2])

    @property
    def pending_save(self) -> list[str]:
        if not self.get("configfile", "save_config_pending", False):
            return []
        return list(self.get("configfile", "save_config_pending_items", {}) or {})

    def extra_fans(self) -> list[str]:
        return [
            name
            for name in self.objects
            if name.startswith("fan_generic ") and name != machine.CHAMBER_FAN
        ]
