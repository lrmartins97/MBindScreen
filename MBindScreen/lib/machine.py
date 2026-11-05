"""What is specific to the M-BIND: names of its Klipper objects and small pure
helpers. No Qt here, so everything in this file can be unit tested.

If the machine configuration (m-bind-config) renames something, this file and
gcodeCommands.py are the only places to change.
"""
from __future__ import annotations

import math
import typing

TOOLS = (0, 1)
EXTRUDERS = {0: "extruder", 1: "extruder1"}
CHAMBER_FAN = "fan_generic Chamber_Fan"
UV_PIN = "output_pin UV"
CHAMBER_LIGHT = "output_pin Led_Chamber"
SERINGA_VARS = "gcode_macro _SERINGA_VARS"
ALIGN_VARS = "gcode_macro _ALIGN_VARS"
MATERIAL_PREFIX = "gcode_macro _MATERIAL_"

# Values from the configuration, used until Klipper reports the real ones.
DEFAULT_MAX_TEMP = 90.0
DEFAULT_SYRINGE_DIAMETER = 15.0
DEFAULT_MAX_PLUNGER_MM = 20.0
DEFAULT_MAX_PLUNGER_SPEED = 3.0

JOG_SPEED_XY = 50.0  # mm/s
JOG_SPEED_Z = 5.0  # mm/s, max_z_velocity in hardware/eixos.cfg
Z_JOG_MIN = 0.0  # the plate rises towards the nozzle: never jog it past Z=0

ACTIVE_PRINT_STATES = ("printing", "paused")
PRINT_STATE_TITLES = {
    "standby": "Pronta",
    "printing": "A imprimir",
    "paused": "Em pausa",
    "complete": "Impressão concluída",
    "cancelled": "Impressão cancelada",
    "error": "Erro na impressão",
}
KLIPPY_TITLES = {
    "ready": "Pronta",
    "startup": "A arrancar",
    "shutdown": "Paragem de emergência",
    "error": "Erro no Klipper",
    "disconnected": "Klipper desligado",
}
# M117 messages from PRINT_START, in order (impressao/inicio_fim.cfg).
PREPARE_STAGES = (
    ("A preparar...", "Preparar"),
    ("Home...", "Home"),
    ("A aquecer...", "Aquecer"),
    ("A calibrar...", "Calibrar"),
    ("A limpar...", "Limpar"),
    ("Linha de purga", "Purga"),
)
PRINTING_MESSAGE = "A imprimir"


def syringe_area(diameter: float) -> float:
    """Plunger area in mm2."""
    return math.pi * (diameter / 2) ** 2


def plunger_volume(mm: float, diameter: float) -> float:
    """mm3 pushed by moving the plunger ``mm``."""
    return abs(mm) * syringe_area(diameter)


def format_volume(mm3: float) -> str:
    """Volume for the screen: mL from 1000 mm3 up (1 mm3 = 1 uL)."""
    if mm3 >= 1000:
        return f"{mm3 / 1000:.2f} mL"
    return f"{mm3:.0f} µL"


def format_time(seconds: typing.Optional[float]) -> str:
    if seconds is None:
        return "—"
    total = int(max(seconds, 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m {secs:02d}s"


def remaining_time(
    progress: float, elapsed: float, estimate: typing.Optional[float]
) -> typing.Optional[float]:
    """Time left: from real progress once there is enough, else the slicer estimate."""
    if progress >= 0.02 and elapsed > 0:
        return elapsed * (1 - progress) / progress
    return max(estimate - elapsed, 0) if estimate else None


def clamp_jog(position: float, delta: float, minimum: float, maximum: float) -> float:
    """Part of ``delta`` that stays inside the limits (0 if there is no room)."""
    target = min(max(position + delta, minimum), maximum)
    moved = target - position
    if abs(moved) < 1e-6 or (moved > 0) != (delta > 0):
        return 0.0
    return round(moved, 3)


def prepare_stage(message: str) -> int:
    """Index of the PRINT_START stage for a display message, -1 if it is not one."""
    for index, (text, _) in enumerate(PREPARE_STAGES):
        if message == text:
            return index
    return -1


def material_slots(objects: typing.Iterable[str]) -> list[int]:
    """Numbers of the materials defined in impressao/materiais.cfg."""
    slots = []
    for name in objects:
        suffix = name[len(MATERIAL_PREFIX):]
        if name.startswith(MATERIAL_PREFIX) and suffix.isdigit():
            slots.append(int(suffix))
    return sorted(slots)


def unsafe_pending_save(items: typing.Iterable[str]) -> list[str]:
    """Pending SAVE_CONFIG sections that must not be saved on this machine.

    With dual_carriage, Klipper refuses to start with an [input_shaper] written
    by SAVE_CONFIG (see "Nao repetir" in the m-bind-config CLAUDE.md).
    """
    return [name for name in items if name.lower().startswith("input_shaper")]
