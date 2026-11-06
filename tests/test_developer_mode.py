"""Developer mode: what is hidden from everyday use, and the code that shows it."""
import hashlib

import pytest
from conftest import click_button, top_dialog
from lib.panels.mainWindow import SETTINGS
from lib.panels.settingsTab import MENU_COLUMNS

CODE = "9182"


@pytest.fixture
def tab(window, qtbot):
    settings = window.settings
    settings.developer_code = hashlib.sha256(CODE.encode()).hexdigest()
    window.goto(SETTINGS)
    qtbot.waitUntil(settings.developer.isVisible, timeout=1000)
    return settings


def enter(window, code):
    window.settings.developer.clicked.emit()
    dialog = top_dialog(window)
    for digit in code:
        click_button(dialog, digit)
    click_button(dialog, "OK")


def titles(tab):
    return [row.title.text() for row in tab.rows.values() if not row.isHidden()]


def test_screen_switch_updates_and_restart_start_hidden(tab):
    assert titles(tab) == ["Mensagens", "Rede", "Sistema"]


def test_the_right_code_shows_them(tab, window):
    enter(window, CODE)
    assert "Ecrã" in titles(tab) and "Atualizações" in titles(tab) and "Reiniciar" in titles(tab)


def test_a_wrong_code_shows_nothing_and_says_so(tab, window):
    enter(window, "0000")
    assert titles(tab) == ["Mensagens", "Rede", "Sistema"]
    assert tab.developer.description.text() == "Código errado."


def test_leaving_hides_them_again(tab, window):
    enter(window, CODE)
    tab.developer.clicked.emit()
    assert titles(tab) == ["Mensagens", "Rede", "Sistema"]


def test_the_menu_keeps_no_holes(tab):
    positions = {
        tab.grid.getItemPosition(tab.grid.indexOf(row))[:2]
        for row in (*tab.rows.values(), tab.language, tab.developer) if not row.isHidden()
    }
    expected = {(i // MENU_COLUMNS, i % MENU_COLUMNS) for i in range(len(positions))}
    assert positions == expected


def test_the_code_itself_is_not_in_the_source():
    from configfile import DEFAULT_DEVELOPER_CODE

    assert len(DEFAULT_DEVELOPER_CODE) == 64
