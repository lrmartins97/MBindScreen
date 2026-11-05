"""Manual X/Y calibration: camera, jog and the steps of the macros."""
import pytest
from conftest import click_button, click_jog, top_dialog
from lib import gcodeCommands as gc
from lib.panels.alignPage import AlignPage
from lib.panels.widgets.cameraView import MISSED_FRAMES_FOR_WARNING, CameraView
from lib.runner import Runner
from PyQt6 import QtCore, QtGui


@pytest.fixture
def started(window, api):
    window.goto(3)
    window.calibration._run("Calibração X/Y", gc.calibrate_xy(manual=True))
    return window


def box_title(window):
    return window.overlays[3].title.text()


def test_page_opens_on_the_camera_instead_of_a_dialog(started, qtbot):
    page = started.align
    assert isinstance(page, AlignPage)
    assert page.isVisible()
    assert not started.overlays[2].isVisible()  # no prompt dialog
    assert not started.overlays[3].isVisible()  # no routine box
    assert "T0" in page.title.text()
    assert "centro da mira" in page.step.text()
    qtbot.waitUntil(lambda: page.camera.has_image, timeout=2000)


def test_page_also_opens_when_started_from_mainsail(window, api):
    api.gcode("CALIBRATE_IDEX_XY MANUAL=1")
    assert window.align.isVisible()


def test_jog_uses_the_macro_with_the_chosen_step(started, api):
    page = started.align
    page.steps.select(0)  # 0.01 mm
    click_jog(page, "X+")
    assert api.sent[-1] == "_ALIGN_JOG X=0.01"
    page.steps.select(4)  # 1 mm
    click_jog(page, "Y-")
    assert api.sent[-1] == "_ALIGN_JOG Y=-1"


def test_jog_moves_the_head_and_the_position_follows(started, api):
    page = started.align
    start = started.printer.position("x")
    page.steps.select(2)  # 0.1 mm
    click_jog(page, "X-")
    assert started.printer.position("x") == pytest.approx(start - 0.1)
    assert f"{start - 0.1:.2f}" in page.position.text()


def test_arrows_point_the_way_the_head_moves(started):
    grid = started.align.jog_buttons[0].parentWidget().layout().itemAt(0).layout()
    place = {
        b.accessibleName(): grid.getItemPosition(grid.indexOf(b))[:2]
        for b in started.align.jog_buttons
    }
    assert place["X+"][1] > place["X-"][1]  # right is further right
    assert place["Y+"][0] < place["Y-"][0]  # up is higher


def test_camera_image_is_mirrored_like_in_mainsail(started):
    assert started.align.camera.transform.m11() == -1
    assert started.align.camera.transform.m22() == 1


def test_full_sequence_t0_then_t1_then_done(started, api):
    page = started.align
    click_button(page, "Seguinte")
    assert api.sent[-1] == "CALIBRATE_IDEX_NEXT"
    assert page.isVisible() and "T1" in page.title.text()
    assert not started.overlays[3].isVisible()  # waiting for the user, not "done"
    click_button(page, "Seguinte")
    assert not page.isVisible()
    assert started.overlays[3].isVisible() and box_title(started) == "Concluído"
    assert "concluida" in started.overlays[3].text.text()  # the macro's own last line


def test_buttons_are_off_while_the_head_travels(started, api):
    page = started.align
    api.gcode_response.emit("// action:prompt_end")  # the macro took over
    assert page.isVisible()
    assert not page.next.isEnabled()
    assert not any(b.isEnabled() for b in page.jog_buttons)
    assert page.cancel.isEnabled()  # never trapped if a macro step failed


def test_status_arriving_after_the_answer_shows_no_false_done(started, api, qtbot, monkeypatch):
    """On a real printer the next prompt can arrive just after the script's answer."""
    page = started.align
    monkeypatch.setattr(Runner, "SETTLE_MS", 80)
    original = api.gcode

    def late(script, callback=None):
        api.gcode_response.emit("// action:prompt_end")
        callback("ok", None)
        QtCore.QTimer.singleShot(20, lambda: original(script))

    api.gcode = late
    started.runner.start("Calibração X/Y", gc.ALIGN_NEXT)
    assert started.runner.running  # still waiting right after the answer
    qtbot.waitUntil(lambda: not started.runner.running, timeout=1000)
    assert not started.runner.finished
    assert not started.overlays[3].isVisible()
    assert "T1" in page.title.text() and page.next.isEnabled()


def test_failed_step_leaves_a_way_out(started, api):
    page = started.align
    original = api.gcode

    def fails(script, callback=None):
        if script == gc.ALIGN_NEXT:
            api.gcode_response.emit("// action:prompt_end")
            callback(None, {"message": "Offset demasiado grande"})
        else:
            original(script, callback)

    api.gcode = fails
    click_button(page, "Seguinte")
    assert box_title(started) == "Falhou"
    click_button(started.overlays[3], "OK")
    assert page.isVisible()
    click_button(page, "Cancelar")
    click_button(top_dialog(started), "Cancelar calibração")
    assert api.sent[-1] == "CALIBRATE_IDEX_CANCEL"
    assert not page.isVisible()


def test_cancel_needs_confirmation(started, api):
    click_button(started.align, "Cancelar")
    assert "CALIBRATE_IDEX_CANCEL" not in api.sent
    click_button(top_dialog(started), "Voltar")
    assert started.align.isVisible()
    assert "CALIBRATE_IDEX_CANCEL" not in api.sent


def test_emergency_stop_is_on_the_page(started, api):
    click_button(started.align, "Parar")
    click_button(top_dialog(started), "PARAR")
    assert ("printer.emergency_stop", None) in api.calls


def test_full_calibration_with_xy_by_the_mark_opens_the_page(window, api):
    window.calibration._run("Calibração", gc.calibrate_idex(xy_manual=True))
    assert window.align.isVisible()


def test_camera_shows_a_message_when_the_image_stops(started, api, qtbot):
    camera = started.align.camera
    qtbot.waitUntil(lambda: camera.has_image, timeout=2000)
    api.camera_ok = False
    qtbot.waitUntil(lambda: camera.missed >= MISSED_FRAMES_FOR_WARNING, timeout=3000)
    assert not camera.has_image
    api.camera_ok = True
    qtbot.waitUntil(lambda: camera.has_image, timeout=2000)


def test_camera_stops_asking_when_the_page_closes(started, api, qtbot):
    click_button(started.align, "Seguinte")
    click_button(started.align, "Seguinte")
    assert not started.align.isVisible()
    qtbot.wait(200)  # let an answer already on its way arrive
    count = api.camera_requests
    qtbot.wait(300)
    assert api.camera_requests == count


def test_zoom_keeps_the_centre_of_the_image(qapp, qtbot, api):
    view = CameraView(api, "/cam")
    qtbot.addWidget(view)
    frame = QtGui.QPixmap(640, 480)
    frame.fill(QtGui.QColor("#ffffff"))
    painter = QtGui.QPainter(frame)
    painter.fillRect(QtCore.QRect(319, 239, 2, 2), QtGui.QColor("#000000"))
    painter.end()
    view.frame = frame
    view.set_zoom(4)
    part = view._visible_part()
    assert (part.width(), part.height()) == (160, 120)
    image = part.toImage()
    assert image.pixelColor(80, 60).black() > 200 or image.pixelColor(79, 59).black() > 200


def test_subscription_includes_the_calibration_state():
    from lib import machine
    from lib.moonrakerComm import build_subscription

    subs = build_subscription([machine.ALIGN_VARS])
    assert subs[machine.ALIGN_VARS] == ["active", "origin_set", "mode"]
