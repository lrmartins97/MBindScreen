"""Whole-window flows: tap the real buttons, check what reaches the printer."""
import pathlib

import pytest

from configfile import ScreenConfig
from conftest import click_button, click_jog, top_dialog
from lib import machine, screenSwitch
from lib.moonrakerComm import (
    allowed_when_read_only,
    build_subscription,
    is_own_update_done,
)
from lib.panels.mainWindow import CONTROL, HOME, SETTINGS, SYRINGES, MainWindow
from lib.panels.widgets.dialogs import Scrim
from lib.utils.theme import QSS
from lib.utils.widgets import HOLD_MS
from PyQt6 import QtCore


def test_starts_connected_on_home(window):
    assert window.printer.ready
    assert window.stack.currentIndex() == HOME
    assert not window.overlays[0].isVisible()


def test_plunger_buttons_send_the_chosen_distance_and_speed(window, api):
    window.goto(SYRINGES)
    tab = window.syringes
    tab.distance.select(3)  # 5 mm
    tab.speed.select(0)  # 0.1 mm/s
    tab.panels[1].advance.click()
    tab.panels[0].retract.click()
    assert api.sent[-2:] == ["SERINGA_T1 MM=5 SPEED=0.1", "SERINGA_T0 MM=-5 SPEED=0.1"]


def test_material_choice_is_saved(window, api, qtbot):
    window.goto(SYRINGES)
    window.syringes.panels[1].material.click()
    click_button(window, "Pasta 2")
    assert api.sent[-1] == "SET_MATERIAL TOOL=1 MATERIAL=2"
    qtbot.waitUntil(lambda: window.syringes.panels[1].material.text() == "Pasta 2")


def test_temperature_keypad_refuses_above_the_machine_limit(window, api):
    window.goto(SYRINGES)
    window.syringes.panels[0].held.emit()
    pad = top_dialog(window)
    click_button(pad, "9")
    click_button(pad, "5")
    ok = [b for b in pad.findChildren(type(window.syringes.panels[0].advance))
          if b.text() == "OK"][0]
    assert not ok.isEnabled()
    click_button(pad, "⌫")
    click_button(pad, "⌫")
    click_button(pad, "3")
    click_button(pad, "7")
    click_button(pad, "OK")
    assert api.sent[-1] == "SET_HEATER_TEMPERATURE HEATER=extruder TARGET=37"


def test_jog_needs_home_and_never_passes_z_zero(window, api):
    window.goto(CONTROL)
    tab = window.control
    assert not any(b.isEnabled() for b in tab.jog_buttons)
    api.gcode("G28")
    assert all(b.isEnabled() for b in tab.jog_buttons)
    tab.distances.select(3)  # 50 mm
    plate_up = next(b for b in tab.jog_buttons if b.text().endswith("▲"))
    plate_up.click()
    assert api.sent[-1] == "G91\nG1 Z-8 F300\nG90"  # homed at Z=8: stops at 0
    plate_up.click()
    assert api.sent[-1].startswith("G91\nG1 Z-8")  # nothing else sent
    assert "Limite" in tab.hint.text()


def test_jog_arrows_move_the_head_the_way_they_point(window, api):
    window.goto(CONTROL)
    api.gcode("G28")
    window.control.distances.select(1)
    click_jog(window.control, "X+")
    assert " X" in api.sent[-1].replace("G1", "") and "-" not in api.sent[-1]
    assert not window.control.jog_buttons[0].text()  # an arrow, no X/Y letters


def test_uv_asks_for_confirmation_before_turning_on(window, api):
    window.goto(CONTROL)
    window.control._set_uv(50)
    assert not any("PIN=UV" in s for s in api.sent)
    click_button(window, "Ligar UV")
    assert api.sent[-1] == "SET_PIN PIN=UV VALUE=0.50"


def test_print_page_opens_by_itself_and_blocks_manual_actions(window, api, qtbot):
    window.goto(SYRINGES)
    api.call("printer.print.start", {"filename": "alginato_grelha.gcode"})
    qtbot.waitUntil(lambda: window.stack.currentWidget() is window.printing)
    window.goto(SYRINGES)
    assert not window.syringes.panels[0].advance.isEnabled()
    assert not window.control.home.isEnabled()
    assert all(not row.isEnabled() for row in window.calibration.rows)


def test_print_shows_prepare_stage_then_progress(window, api, qtbot):
    api.call("printer.print.start", {"filename": "alginato_grelha.gcode"})
    qtbot.waitUntil(lambda: window.printing.stages.isVisible())
    assert window.printing.status.text() == machine.PREPARE_STAGES[0][0]
    api.state["display_status"]["message"] = machine.PRINTING_MESSAGE
    api.status.emit(api.state)
    assert not window.printing.stages.isVisible()


def test_babystep_is_relative_and_limited(window, api):
    api.gcode("G28")
    api.call("printer.print.start", {"filename": "alginato_grelha.gcode"})
    window.printing.z_steps.select(1)  # 0.05
    window.printing._babystep(1)
    assert api.sent[-1] == "SET_GCODE_OFFSET Z_ADJUST=0.05 MOVE=1"
    api.state["gcode_move"]["homing_origin"][2] = 1.0
    count = len(api.sent)
    window.printing._babystep(1)
    assert len(api.sent) == count


def test_cancel_needs_confirmation(window, api):
    api.call("printer.print.start", {"filename": "alginato_grelha.gcode"})
    click_button(window.printing, "Cancelar impressão")
    assert not any(c[0] == "printer.print.cancel" for c in api.calls)
    click_button(top_dialog(window), "Cancelar impressão")
    assert any(c[0] == "printer.print.cancel" for c in api.calls)


def test_paper_test_flow_follows_klipper_state(window, api):
    overlay = window.overlays[1]
    window.calibration._z_t0()
    assert overlay.isVisible()
    assert not window.overlays[3].isVisible()  # the routine box steps aside
    click_button(overlay, "-0.05")
    assert api.sent[-1] == "TESTZ Z=-0.05"
    click_button(overlay, "Aceitar")
    assert not overlay.isVisible()
    assert window.printer.pending_save == ["stepper_z"]
    assert window.calibration.save_button.isEnabled()


def test_input_shaper_pending_blocks_save_config(window, api):
    api.state["configfile"].update(
        save_config_pending=True, save_config_pending_items={"input_shaper": {}}
    )
    api.status.emit(api.state)
    assert window.calibration.save_button.isHidden()
    assert "input shaper" in window.calibration.save_text.text()


def test_every_popup_fits_its_content(window, api):
    from conftest import top_dialog

    window.calibration._z_t0()
    overlay = window.overlays[1]
    grid = overlay.steps.layout()
    assert overlay.steps.height() >= grid.totalMinimumSize().height()
    assert overlay.box.height() <= window.height()
    click_button(overlay, "Cancelar")
    window.printing._cancel()
    box = top_dialog(window).box
    assert box.height() >= box.layout().totalMinimumSize().height()


def test_bed_screws_flow(window, api):
    overlay = window.overlays[1]
    window.calibration._bed()
    assert overlay.isVisible() and "parafusos" in overlay.title.text()
    for _ in range(3):
        click_button(overlay, "Aceitar")
    assert not overlay.isVisible()


def test_ordinary_prompt_still_opens_as_a_dialog(window, api):
    dialog = window.overlays[2]
    for line in (
        "// action:prompt_begin Aviso",
        "// action:prompt_text Confirma?",
        "// action:prompt_footer_button Sim|RESPOND MSG=ok|primary",
        "// action:prompt_show",
    ):
        api.gcode_response.emit(line)
    assert dialog.isVisible()
    assert not window.align.isVisible()
    click_button(dialog, "Sim")
    assert api.sent[-1] == "RESPOND MSG=ok"
    api.gcode_response.emit("// action:prompt_end")
    assert not dialog.isVisible()


def test_routine_box_reports_a_failure(window, api):
    api.gcode = _failing(api.gcode)
    window.runner.start("Teste", "CALIBRATE_IDEX")
    assert window.overlays[3].isVisible()
    assert window.overlays[3].title.text() == "Falhou"
    click_button(window.overlays[3], "OK")
    assert not window.overlays[3].isVisible()


def _failing(_gcode):
    def run(_script, callback=None):
        callback(None, {"message": "Sem Z calibrado"})

    return run


def test_klipper_error_appears_in_the_badge(window, api):
    api.state["print_stats"]["state"] = "printing"
    api.gcode("SERINGA_T0 MM=1 SPEED=0.5")
    assert window.printer.alerts
    assert window.nav.badge.isVisibleTo(window.nav)
    assert window.stack.indexOf(window.settings) == SETTINGS


def test_shutdown_shows_recovery_page(window, api):
    click = window.overlays[0]
    window.emergency_stop()
    click_button(window, "PARAR")
    assert click.isVisible()
    click_button(click, "Reiniciar firmware")
    assert ("printer.firmware_restart", None) in api.calls
    assert not click.isVisible()


def test_switch_records_choice_and_restores_it_on_error(tmp_path: pathlib.Path, api, monkeypatch):
    boot = tmp_path / "boot-screen"
    screenSwitch.write_boot_screen(screenSwitch.MBIND, boot)
    api.open()
    screenSwitch.switch_to_klipperscreen(api, lambda _m: None, boot)
    assert ("machine.services.start", {"service": "KlipperScreen"}) in api.calls
    assert screenSwitch.read_boot_screen(boot) == screenSwitch.KLIPPERSCREEN

    class Refusing:
        def call(self, _method, _params, callback):
            callback(None, {"message": "Service 'KlipperScreen' not allowed"})

    screenSwitch.write_boot_screen(screenSwitch.MBIND, boot)
    errors = []
    monkeypatch.setattr(screenSwitch, "start_directly", lambda: True)
    screenSwitch.switch_to_klipperscreen(Refusing(), errors.append, boot)
    assert not errors and screenSwitch.read_boot_screen(boot) == screenSwitch.KLIPPERSCREEN

    screenSwitch.write_boot_screen(screenSwitch.MBIND, boot)
    monkeypatch.setattr(screenSwitch, "start_directly", lambda: False)
    screenSwitch.switch_to_klipperscreen(Refusing(), errors.append, boot)
    assert errors and screenSwitch.read_boot_screen(boot) == screenSwitch.MBIND


def test_boot_file_defaults_to_klipperscreen(tmp_path):
    assert screenSwitch.read_boot_screen(tmp_path / "missing") == "klipperscreen"


def test_only_a_finished_update_of_this_app_restarts_it():
    assert is_own_update_done({"application": "MBindScreen", "complete": True})
    assert not is_own_update_done({"application": "MBindScreen", "complete": False})
    assert not is_own_update_done({"application": "klipper", "complete": True})


def test_every_method_the_screen_uses_is_classified_for_read_only():
    """A new write call must not slip through the trial mode unnoticed."""
    import re

    source_dir = pathlib.Path(__file__).resolve().parents[1] / "MBindScreen" / "lib"
    methods = set()
    for path in source_dir.rglob("*.py"):
        if path.name != "simulator.py":
            methods |= set(re.findall(
                r'"((?:printer|machine|server)\.[a-z_]+(?:\.[a-z_]+)*)"',
                path.read_text(encoding="utf-8"),
            ))
    allowed = {m for m in methods if allowed_when_read_only(m)}
    assert methods - allowed == {
        "printer.gcode.script", "printer.print.start", "printer.print.pause",
        "printer.print.resume", "printer.print.cancel", "printer.restart",
        "printer.firmware_restart", "machine.reboot", "machine.shutdown",
        "machine.update.refresh", "machine.update.upgrade",
    }


def test_subscription_only_asks_for_existing_objects():
    subs = build_subscription(["toolhead", "extruder", "gcode_macro _MATERIAL_3",
                               "gcode_macro _MATERIAL_STATE"])
    assert "heater_bed" not in subs and "extruder1" not in subs
    assert subs["gcode_macro _MATERIAL_3"] == ["name"]


@pytest.mark.parametrize("read_only", [False, True])
def test_every_page_fits_the_screen(qtbot, qapp, api, read_only):
    """A taller window is cut at the bottom edge, emergency stop included."""
    qapp.setStyleSheet(QSS)
    win = MainWindow(ScreenConfig(), api, read_only)
    qtbot.addWidget(win)
    assert win.minimumSizeHint().height() <= 480


def test_a_touch_on_a_syringe_selects_it_and_only_holding_sets_the_temperature(
    window, api, qtbot
):
    window.goto(SYRINGES)
    panel = window.syringes.panels[1]
    qtbot.mouseClick(panel, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(8, 8))
    assert api.sent[-1] == "SERINGA_T1"  # no home yet
    assert not any(s.isVisible() for s in window.findChildren(Scrim))
    sent = len(api.sent)
    qtbot.mousePress(panel, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(8, 8))
    qtbot.wait(HOLD_MS + 100)
    assert top_dialog(window).isVisible()
    qtbot.mouseRelease(panel, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(8, 8))
    assert len(api.sent) == sent  # the end of a hold selects nothing


def test_holding_a_syringe_switches_to_that_head_while_setting_its_temperature(window, api):
    window.goto(SYRINGES)
    assert window.printer.active_tool == 0
    window.syringes.panels[1].held.emit()
    assert api.sent[-1] == "SERINGA_T1"  # no home yet
    assert top_dialog(window).isVisible()


def test_jog_of_the_second_head_moves_only_the_step_chosen(window, api):
    """Parked past the limits of the T0: 1 mm used to become a jump to that limit."""
    api.gcode("G28")
    api.gcode("T1")
    window.goto(CONTROL)
    window.control.distances.select(1)  # 1 mm
    click_jog(window.control, "X-")
    assert api.sent[-1] == "G91\nG1 X-1 F3000\nG90"


def test_second_head_stops_at_its_own_limit(window, api):
    api.gcode("G28")
    api.gcode("T1")
    window.goto(CONTROL)
    window.control.distances.select(3)  # 50 mm, parked 10 mm from the limit
    click_jog(window.control, "X+")
    assert api.sent[-1] == "G91\nG1 X10 F3000\nG90"


def test_without_home_a_head_is_chosen_without_moving_any_axis(window, api):
    window.goto(CONTROL)
    assert not window.printer.homed()
    window.control.tool_buttons[1].click()
    assert api.sent[-1] == "SERINGA_T1"
    assert window.printer.active_tool == 1
    assert window.printer.tool(1).active and not window.printer.tool(0).active
    assert not window.printer.alerts


def test_with_home_a_head_is_changed_with_the_tool_macro(window, api):
    api.gcode("G28")
    window.goto(CONTROL)
    window.control.tool_buttons[1].click()
    assert api.sent[-1] == "T1"


def test_home_puts_the_selection_back_on_the_head_really_active(window, api):
    window.control.tool_buttons[1].click()
    api.gcode("G28")
    assert window.printer.active_tool == 0


def test_cards_of_the_main_page_select_the_head(window, api, qtbot):
    card = window.home.tools[1]
    qtbot.mouseClick(card, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(8, 8))
    assert api.sent[-1] == "SERINGA_T1"
    assert window.stack.currentIndex() == HOME  # stays on the page


def test_holding_a_card_of_the_main_page_opens_its_temperature(window, api):
    window.home.tools[1].held.emit()
    assert api.sent[-1] == "SERINGA_T1"
    assert top_dialog(window).isVisible()
