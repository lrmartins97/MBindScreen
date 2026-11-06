"""Dialogs must really be on screen: code can press a button nobody can see."""
import pytest
from conftest import click_button
from lib.panels.widgets.dialogs import choose, code_pad, confirm, keyboard, numpad
from PyQt6 import QtCore, QtWidgets

DIALOGS = {
    "choose": lambda window: choose(window, "Título", (("A", 1), ("B", 2), ("C", 3)), print),
    "confirm": lambda window: confirm(window, "Texto " * 40, print),
    "numpad": lambda window: numpad(window, "Temperatura", 30, 90, print),
    "keyboard": lambda window: keyboard(window, "Palavra-passe", print, 8),
    "code_pad": lambda window: code_pad(window, "Código", print, 4),
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


def test_keyboard_types_capitals_symbols_and_waits_for_the_minimum(window):
    typed = []
    scrim = keyboard(window, "Palavra-passe", typed.append, 4)
    ok = next(b for b in scrim.findChildren(QtWidgets.QPushButton) if b.text() == "Ligar")
    assert not ok.isEnabled()
    click_button(scrim, "a")
    click_button(scrim, "⇧")
    click_button(scrim, "B")
    click_button(scrim, "⇧")
    click_button(scrim, "#+=")
    click_button(scrim, "!")
    click_button(scrim, "abc")
    click_button(scrim, "1")
    click_button(scrim, "espaço")
    click_button(scrim, "⌫")
    assert ok.isEnabled()
    ok.click()
    assert typed == ["aB!1"]


def test_code_pad_hides_the_digits_and_waits_for_the_minimum(window):
    typed = []
    scrim = code_pad(window, "Código", typed.append, 4)
    ok = next(b for b in scrim.findChildren(QtWidgets.QPushButton) if b.text() == "OK")
    for key in "12*":
        click_button(scrim, key)
    assert not ok.isEnabled()
    click_button(scrim, "#")
    click_button(scrim, "⌫")
    click_button(scrim, "0")
    display = next(w for w in scrim.findChildren(QtWidgets.QLabel)
                   if w.objectName() == "display")
    assert display.text() == "●●●●"
    ok.click()
    assert typed == ["12*0"]


def test_keyboard_can_write_every_character_of_a_password():
    import string

    from lib.panels.widgets.dialogs import KEY_LAYERS

    available = "".join("".join(layer) for layer in KEY_LAYERS)
    missing = set(string.printable[:94].lower()) - set(available.lower())
    assert not missing


def test_touching_outside_closes_it(box, qtbot, window):
    if box.box.width() >= window.width() - 30:
        pytest.skip("the keyboard takes the whole width")
    qtbot.mouseClick(box, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(5, 5))
    assert not box.isVisible()


def test_touching_the_box_itself_keeps_it_open(box, qtbot):
    qtbot.mouseClick(box.box, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(3, 3))
    assert box.isVisible()
