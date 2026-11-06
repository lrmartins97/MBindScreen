"""What is specific to the M-BIND: names of its Klipper objects and small pure
helpers. No Qt here, so everything in this file can be unit tested.

If the machine configuration (m-bind-config) renames something, this file and
gcodeCommands.py are the only places to change.
"""
from __future__ import annotations

import dataclasses
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


# Names as they are in Mainsail on the machines; any other name is shown as it is.
CAMERA_NAMES = {
    "chamber": "Interior",
    "nozzle cam": "Alinhar bicos",
    "tool 0": "Seringa T0",
    "tool 1": "Seringa T1",
}
NOZZLESIGHT_IMAGE = "/ktamv/"  # the nozzle camera again, with the vision server's analysis
NOZZLESIGHT_NAME = "NozzleSight"


@dataclasses.dataclass(frozen=True)
class Camera:
    name: str
    path: str
    flip_horizontal: bool = False
    flip_vertical: bool = False
    rotation: int = 0
    is_analysis: bool = False


def cameras_from_webcams(webcams: typing.Iterable[dict]) -> list[Camera]:
    """What Moonraker's server.webcams.list gives, reduced to what the screen shows."""
    cameras = [
        Camera(
            NOZZLESIGHT_NAME if NOZZLESIGHT_IMAGE in webcam["snapshot_url"]
            else CAMERA_NAMES.get(webcam["name"].lower(), webcam["name"]),
            webcam["snapshot_url"],
            webcam.get("flip_horizontal", False),
            webcam.get("flip_vertical", False),
            webcam.get("rotation", 0),
            NOZZLESIGHT_IMAGE in webcam["snapshot_url"],
        )
        for webcam in webcams
        if webcam.get("enabled", True) and webcam.get("snapshot_url")
    ]
    return sorted(cameras, key=lambda camera: (camera.is_analysis, camera.name.lower()))


MAIN_BOARD = "mcu"
BOARD_PREFIX = "mcu "


def board_objects(objects: typing.Iterable[str]) -> list[str]:
    """Klipper objects that are a board: the main one first."""
    return sorted(
        (o for o in objects if o == MAIN_BOARD or o.startswith(BOARD_PREFIX)),
        key=lambda name: (name != MAIN_BOARD, name),
    )


def board_chip(constants: dict) -> str:
    """stm32h723xx becomes STM32H723."""
    return str(constants.get("MCU", "?")).upper().removesuffix("XX")


def syringe_area(diameter: float) -> float:
    """Plunger area in mm2."""
    return math.pi * (diameter / 2) ** 2


def plunger_volume(mm: float, diameter: float) -> float:
    """mm3 pushed by moving the plunger ``mm``."""
    return abs(mm) * syringe_area(diameter)


def format_volume(mm3: float) -> str:
    """Volume for the screen, always in mL (1000 mm3 = 1 mL)."""
    return f"{mm3 / 1000:.3f} mL"


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
    """Part of ``delta`` that stays inside the limits (0 if there is no room).
    Never more than ``delta``: a jog must not jump back from outside the limits."""
    target = min(max(position + delta, minimum), maximum)
    moved = target - position
    if abs(moved) < 1e-6 or (moved > 0) != (delta > 0):
        return 0.0
    return round(min(moved, delta) if delta > 0 else max(moved, delta), 3)


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
