import pytest
from lib import gcodeCommands as gc
from lib import machine
from lib.prompts import PromptParser, parse_button


def test_syringe_volume_uses_the_15_mm_barrel():
    assert machine.plunger_volume(1, 15) == pytest.approx(176.71, abs=0.01)
    assert machine.plunger_volume(-1, 15) == pytest.approx(176.71, abs=0.01)


@pytest.mark.parametrize(
    "mm3, text", [(88.4, "0.088 mL"), (176.7, "0.177 mL"), (883.6, "0.884 mL"), (1767, "1.767 mL")]
)
def test_format_volume(mm3, text):
    assert machine.format_volume(mm3) == text


@pytest.mark.parametrize(
    "position, delta, low, high, expected",
    [
        (10, 5, 0, 30, 5),
        (10, -5, 0, 30, -5),
        (2, -5, 0, 30, -2),  # stops at the limit
        (0, -1, 0, 30, 0),  # already at the limit
        (-0.5, 1, 0, 30, 1),  # below the limit, moving away is allowed
        (-0.5, -1, 0, 30, 0),  # below the limit, never further down
        (29, 5, 0, 30, 1),
        (140, -1, 0, 100, -1),  # outside: one step back, never a jump to the limit
    ],
)
def test_clamp_jog(position, delta, low, high, expected):
    assert machine.clamp_jog(position, delta, low, high) == pytest.approx(expected)


def test_remaining_time_prefers_real_progress_and_falls_back_to_estimate():
    assert machine.remaining_time(0.5, 100, 999) == pytest.approx(100)
    assert machine.remaining_time(0.0, 100, 500) == pytest.approx(400)
    assert machine.remaining_time(0.0, 100, None) is None


def test_prepare_stage_matches_print_start_messages():
    assert machine.prepare_stage("A aquecer...") == 2
    assert machine.prepare_stage(machine.PRINTING_MESSAGE) == -1


def test_material_slots_ignores_other_macros():
    names = ["gcode_macro _MATERIAL_2", "gcode_macro _MATERIAL_STATE",
             "gcode_macro _MATERIAL_APPLY", "gcode_macro _MATERIAL_1", "extruder"]
    assert machine.material_slots(names) == [1, 2]


def test_unsafe_pending_save_flags_input_shaper_only():
    assert machine.unsafe_pending_save(["stepper_z", "input_shaper"]) == ["input_shaper"]
    assert machine.unsafe_pending_save(["stepper_z"]) == []


def test_commands():
    assert gc.set_temperature(1, 37) == "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=37"
    assert gc.move_plunger(0, -1, 0.5) == "SERINGA_T0 MM=-1 SPEED=0.5"
    assert gc.jog("Z", -0.1, 5) == "G91\nG1 Z-0.1 F300\nG90"
    assert gc.babystep(-0.01) == "SET_GCODE_OFFSET Z_ADJUST=-0.01 MOVE=1"
    assert gc.calibrate_idex(xy_manual=True) == "CALIBRATE_IDEX Z_MANUAL=0 XY_MANUAL=1"


def test_prompt_parser_reads_the_manual_xy_prompt():
    parser = PromptParser()
    results = [parser.feed(line) for line in (
        "// action:prompt_begin Calibracao X/Y manual",
        "// action:prompt_text Bico T0: centra.",
        "// action:prompt_button_group_start",
        "// action:prompt_button X −0.10|_ALIGN_JOG X=-0.10|info",
        "// action:prompt_button X +0.10|_ALIGN_JOG X=0.10|info",
        "// action:prompt_button_group_end",
        "// action:prompt_footer_button Seguinte|CALIBRATE_IDEX_NEXT|primary",
        "// action:prompt_show",
    )]
    assert results[-1] == "show"
    prompt = parser.prompt
    assert prompt.title == "Calibracao X/Y manual"
    assert len(prompt.rows) == 1 and len(prompt.rows[0]) == 2
    assert prompt.rows[0][0].gcode == "_ALIGN_JOG X=-0.10"
    assert prompt.footer[0].style == "primary"
    assert parser.feed("// action:prompt_end") == "close"
    assert parser.feed("// outra linha") is None


def test_button_without_gcode_sends_its_label():
    assert parse_button("HOME").gcode == "HOME"
