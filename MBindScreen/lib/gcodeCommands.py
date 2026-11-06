"""Every G-code the screen sends is built here, and only here.

To debug "what does this button send?", look in this file.
tests/test_gcode_commands.py checks that each macro used here exists in the
machine configuration.
"""
from __future__ import annotations

from lib import machine

HOME_ALL = "G28"
HOME_IF_NEEDED = "HOME_IF_NEEDED"
MOTORS_OFF = "M84"
TURN_OFF_HEATERS = "TURN_OFF_HEATERS"
SAVE_CONFIG = "SAVE_CONFIG"
ACCEPT = "ACCEPT"
ABORT = "ABORT"
ADJUSTED = "ADJUSTED"
CALIBRATION_STATUS = "CALIBRATE_IDEX_STATUS"
CALIBRATE_FOCUS = "CALIBRATE_IDEX_CAMERA_FOCUS"
MEASURE_RESONANCE = ("CALIBRAR_RESSONANCIA_T0", "CALIBRAR_RESSONANCIA_T1")
CALIBRATE_Z_T0 = "CALIBRAR_Z"
ADJUST_BED = "AJUSTAR_CAMA"
MEASURE_PLATE = "MEASURE_PLATE_HEIGHT"
ALIGN_NEXT = "CALIBRATE_IDEX_NEXT"
ALIGN_CANCEL = "CALIBRATE_IDEX_CANCEL"


def select_tool(tool: int, homed: bool = True) -> str:
    """T0/T1 park the heads, so they need home. SERINGA_Tn alone only picks the
    plunger, without moving any axis; the next G28 puts it back on the active head."""
    return f"T{tool}" if homed else f"SERINGA_T{tool}"


def set_temperature(tool: int, target: float) -> str:
    return f"SET_HEATER_TEMPERATURE HEATER={machine.EXTRUDERS[tool]} TARGET={target:g}"


def jog(axis: str, distance: float, speed: float) -> str:
    return f"G91\nG1 {axis}{distance:g} F{speed * 60:g}\nG90"


def move_plunger(tool: int, mm: float, speed: float) -> str:
    """Plunger of a syringe (+ advances, - retracts). The macro refuses it while printing."""
    return f"SERINGA_T{tool} MM={mm:g} SPEED={speed:g}"


def set_material(tool: int, slot: int) -> str:
    return f"SET_MATERIAL TOOL={tool} MATERIAL={slot}"


def clean_nozzle(tool: int) -> str:
    return f"CLEAN_NOZZLE TOOL={tool}"


def set_fan(fan: str, fraction: float) -> str:
    return f"SET_FAN_SPEED FAN={fan} SPEED={fraction:.2f}"


def set_pin(pin: str, fraction: float) -> str:
    return f"SET_PIN PIN={pin} VALUE={fraction:.2f}"


def babystep(delta: float) -> str:
    """Relative on purpose: the macro keeps the T1 offset under a Z_ADJUST."""
    return f"SET_GCODE_OFFSET Z_ADJUST={delta:g} MOVE=1"


def test_z(delta: float) -> str:
    return f"TESTZ Z={delta:g}"


def calibrate_idex(z_manual: bool = False, xy_manual: bool = False) -> str:
    return f"CALIBRATE_IDEX Z_MANUAL={int(z_manual)} XY_MANUAL={int(xy_manual)}"


def calibrate_xy(manual: bool = False) -> str:
    return f"CALIBRATE_IDEX_XY MANUAL={int(manual)}"


def calibrate_z(manual: bool = False) -> str:
    return f"CALIBRATE_IDEX_Z MANUAL={int(manual)}"


def align_jog(axis: str, distance: float) -> str:
    """Fine move of the manual X/Y calibration. The macro ignores it outside one."""
    return f"_ALIGN_JOG {axis}={distance:g}"


def trim_t1(delta: float) -> str:
    return f"IDEX_Z_TRIM_T1 ADJUST={delta:g}"
