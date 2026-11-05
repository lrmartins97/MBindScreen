"""Cameras tab, with the camera list of a real M-BIND."""
import dataclasses

from lib import machine
from lib.panels.mainWindow import CAMERAS, HOME
from lib.panels.widgets.cameraView import camera_transform
from PyQt6 import QtCore, QtGui


def webcam(name, path, **extra):
    return {"name": name, "enabled": True, "snapshot_url": path, "flip_horizontal": False,
            "flip_vertical": False, "rotation": 0, **extra}


REAL_LIST = [
    webcam("VAOC", "/ktamv/image"),
    webcam("Chamber", "/webcam/?action=snapshot", flip_horizontal=True, flip_vertical=True),
    webcam("Nozzle Cam", "/webcam2/?action=snapshot", flip_vertical=True, rotation=180),
    webcam("tool 1", "/webcam4/?action=snapshot"),
    webcam("tool 0", "/webcam3/?action=snapshot"),
]


def open_tab(window, api, qtbot):
    api.webcams = REAL_LIST
    window.goto(CAMERAS)
    tab = window.cameras
    qtbot.waitUntil(
        lambda: len(tab.tiles) == 4 and all(tile.isVisible() for tile in tab.tiles),
        timeout=2000,
    )
    return tab


def test_cameras_come_with_portuguese_names_without_the_nozzlesight_view():
    cameras = machine.cameras_from_webcams(REAL_LIST)
    assert [c.name for c in cameras] == ["Bicos", "Interior", "Seringa T0", "Seringa T1"]
    assert cameras[0].flip_vertical and cameras[0].rotation == 180
    assert cameras[2].path == "/webcam3/?action=snapshot"


def test_disabled_camera_is_left_out_and_unknown_name_is_kept():
    cameras = machine.cameras_from_webcams(
        [webcam("Off", "/webcam9/", enabled=False), webcam("Prato", "/webcam5/")]
    )
    assert [c.name for c in cameras] == ["Prato"]


def test_grid_shows_every_camera_and_refreshes_each(window, api, qtbot):
    tab = open_tab(window, api, qtbot)
    assert all(tile.isVisible() for tile in tab.tiles)
    assert not tab.message.isVisible()
    qtbot.waitUntil(lambda: all(tile.has_image for tile in tab.tiles), timeout=3000)


def test_tapping_a_camera_opens_it_and_back_returns_to_the_grid(window, api, qtbot):
    tab = open_tab(window, api, qtbot)
    qtbot.mouseClick(tab.tiles[2], QtCore.Qt.MouseButton.LeftButton)
    assert tab.big_views[2].isVisible()
    assert not any(tile.isVisible() for tile in tab.tiles)
    qtbot.waitUntil(lambda: tab.big_views[2].has_image, timeout=2000)
    tab.reset()
    assert all(tile.isVisible() for tile in tab.tiles)


def test_no_camera_is_requested_after_leaving_the_tab(window, api, qtbot):
    open_tab(window, api, qtbot)
    qtbot.wait(150)
    window.goto(HOME)
    qtbot.wait(150)  # what was on its way lands, nothing new starts
    requests = api.camera_requests
    qtbot.wait(1200)
    assert api.camera_requests == requests


def test_opening_the_tab_again_keeps_the_same_views(window, api, qtbot):
    tab = open_tab(window, api, qtbot)
    tiles = list(tab.tiles)
    window.goto(HOME)
    window.goto(CAMERAS)
    assert tab.tiles == tiles


def test_failure_to_list_cameras_is_shown(window, api, qtbot):
    api.webcams = None
    window.goto(CAMERAS)
    assert "lista de câmaras" in window.cameras.message.text()
    assert window.cameras.message.isVisible()


def test_machine_without_cameras_says_so(window, api):
    api.webcams = []
    window.goto(CAMERAS)
    assert window.cameras.message.text() == "Sem câmaras configuradas"


def test_screen_going_to_sleep_stops_the_cameras(window, api, qtbot):
    open_tab(window, api, qtbot)
    window.config = dataclasses.replace(window.config, sleep_minutes=1)
    window._last_touch = -1000.0
    window._check_sleep()
    assert window.stack.currentIndex() == HOME


def pixel_after(transform):
    """A 2x2 image with the top-left pixel marked: where does it end up?"""
    image = QtGui.QImage(2, 2, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("black"))
    image.setPixelColor(0, 0, QtGui.QColor("white"))
    moved = QtGui.QPixmap.fromImage(image).transformed(transform).toImage()
    return [(x, y) for x in range(2) for y in range(2)
            if moved.pixelColor(x, y) == QtGui.QColor("white")]


def test_image_is_turned_as_in_mainsail():
    assert pixel_after(camera_transform(True, False, 0)) == [(1, 0)]
    assert pixel_after(camera_transform(False, True, 0)) == [(0, 1)]
    assert pixel_after(camera_transform(True, True, 0)) == [(1, 1)]
    assert pixel_after(camera_transform(False, False, 180)) == [(1, 1)]
    assert pixel_after(camera_transform(False, True, 180)) == [(1, 0)]  # the nozzle camera
    assert pixel_after(camera_transform(False, False, 90)) == [(1, 0)]
