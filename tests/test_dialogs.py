"""Dialogs must really be on screen: code can press a button nobody can see."""
import pytest
from lib.panels.widgets.dialogs import choose, confirm, numpad
from PyQt6 import QtCore, QtWidgets

DIALOGS = {
    "choose": lambda window: choose(window, "Título", (("A", 1), ("B", 2), ("C", 3)), print),
    "confirm": lambda window: confirm(window, "Texto " * 40, print),
    "numpad": lambda window: numpad(window, "Temperatura", 30, 90, print),
}


@pytest.fixture(params=DIALOGS)
def box(request, window, qtbot):
    scrim = DIALOGS[request.param](window)
    qtbot.waitExposed(scrim)
    return scrim


def test_every_button_is_inside_the_box_and_the_box_inside_the_screen(box, window):
    assert window.rect().contains(box.box.geometry())
    buttons = box.box.findChildren(QtWidgets.QPushButton)
    assert buttons
    for widget in buttons:
        assert widget.isVisible() and widget.height() > 30
        corner = widget.mapTo(box.box, QtCore.QPoint(widget.width(), widget.height()))
        assert box.box.rect().contains(corner - QtCore.QPoint(1, 1))


def test_touching_outside_closes_it(box, qtbot):
    qtbot.mouseClick(box, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(5, 5))
    assert not box.isVisible()


def test_touching_the_box_itself_keeps_it_open(box, qtbot):
    qtbot.mouseClick(box.box, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(3, 3))
    assert box.isVisible()
