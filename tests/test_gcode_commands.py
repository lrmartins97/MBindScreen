"""The screen must only call macros and objects the machine really has.

Reads the m-bind-config folder set in MBIND_CONFIG, or the sibling checkout.
"""
import inspect
import os
import pathlib
import re

import pytest
from lib import gcodeCommands as gc
from lib import machine

CONFIG = pathlib.Path(
    os.environ.get(
        "MBIND_CONFIG", pathlib.Path(__file__).resolve().parents[2] / "m-bind-config"
    )
)
KLIPPER_COMMANDS = {
    "G28", "G91", "G1", "G90", "M84", "SAVE_CONFIG", "ACCEPT", "ABORT", "ADJUSTED",
    "TESTZ", "TURN_OFF_HEATERS", "SET_HEATER_TEMPERATURE", "SET_FAN_SPEED", "SET_PIN",
    "SET_GCODE_OFFSET",
}


@pytest.fixture(scope="module")
def config_text():
    if not CONFIG.is_dir():
        pytest.skip(f"m-bind-config not found at {CONFIG}")
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in CONFIG.rglob("*.cfg")
    )


def sent_words() -> set[str]:
    source = inspect.getsource(gc)
    words = set(re.findall(r'"([A-Z][A-Z0-9_]+)\b', source))
    words |= set(re.findall(r'f"([A-Z][A-Z0-9_]+)\b', source))
    return words


def test_every_macro_exists_in_the_configuration(config_text):
    macros = set(re.findall(r"^\[gcode_macro (\S+)\]", config_text, re.M))
    missing = {
        word
        for word in sent_words() - KLIPPER_COMMANDS
        if word not in macros and not word.startswith("SERINGA_T")
    }
    assert not missing
    assert {"SERINGA_T0", "SERINGA_T1", "T0", "T1"} <= macros


@pytest.mark.parametrize(
    "section",
    ["fan_generic Chamber_Fan", "output_pin UV", "output_pin Led_Chamber",
     "gcode_macro _SERINGA_VARS", "gcode_macro _MATERIAL_1", "bed_screws", "dual_carriage",
     "gcode_macro _ALIGN_VARS"],
)
def test_objects_exist_in_the_configuration(config_text, section):
    assert f"[{section}]" in config_text


def test_named_objects_in_machine_module_exist(config_text):
    for name in (machine.CHAMBER_FAN, machine.UV_PIN, machine.CHAMBER_LIGHT):
        assert f"[{name}]" in config_text


def test_align_macros_exist_with_the_fields_the_page_reads(config_text):
    assert "[gcode_macro _ALIGN_JOG]" in config_text
    for variable in ("active", "origin_set", "mode"):
        assert f"variable_{variable}:" in config_text
    assert gc.ALIGN_NEXT in config_text and gc.ALIGN_CANCEL in config_text
    assert f"action:prompt_footer_button Seguinte|{gc.ALIGN_NEXT}|primary" in config_text


def test_calibration_camera_matches_the_nozzlesight_camera(config_text):
    from configfile import DEFAULT_CALIBRATION_CAMERA

    assert f"http://localhost{DEFAULT_CALIBRATION_CAMERA}" in config_text


def test_prepare_stages_match_print_start(config_text):
    for message, _title in machine.PREPARE_STAGES:
        assert f"M117 {message}" in config_text
    assert f"M117 {machine.PRINTING_MESSAGE}" in config_text
