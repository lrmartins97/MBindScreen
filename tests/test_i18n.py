"""Every interface text has a translation, and English shows no Portuguese."""
import ast
import pathlib
import re

import pytest
from configfile import ScreenConfig
from lib import i18n, machine
from lib.panels import settingsTab
from lib.panels.mainWindow import SETTINGS, MainWindow
from lib.utils.theme import QSS
from PyQt6 import QtCore, QtWidgets

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "MBindScreen" / "lib"
PORTUGUESE_ONLY = re.compile(r"[ãõçáéíóúâêôà]", re.IGNORECASE)


def tr_texts():
    for path in SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "tr":
                argument = node.args[0]
                if isinstance(argument, ast.Constant):
                    yield argument.value, path.name


def test_every_literal_text_has_a_translation():
    missing = {text for text, _ in tr_texts() if text not in i18n.ENGLISH_TEXT}
    assert not missing


def test_names_that_reach_the_screen_through_tables_have_a_translation():
    tables = (*machine.PRINT_STATE_TITLES.values(), *machine.KLIPPY_TITLES.values(),
              *(title for _, title in machine.PREPARE_STAGES), *machine.CAMERA_NAMES.values())
    assert not {text for text in tables if text not in i18n.ENGLISH_TEXT and text != "Home"}


@pytest.mark.parametrize("text, translated", i18n.ENGLISH_TEXT.items())
def test_a_translation_has_the_same_fields_as_the_original(text, translated):
    assert re.findall(r"{[^}]*}", text) == re.findall(r"{[^}]*}", translated)


def test_portuguese_is_the_default_and_values_are_filled(monkeypatch):
    monkeypatch.setattr(i18n, "_language", i18n.PORTUGUESE)
    assert i18n.tr("Sinal {}%", 70) == "Sinal 70%"
    monkeypatch.setattr(i18n, "_language", i18n.ENGLISH)
    assert i18n.tr("Sinal {}%", 70) == "Signal 70%"
    assert i18n.tr("Texto sem tradução") == "Texto sem tradução"


def test_a_saved_language_is_read_and_an_unknown_one_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "LANGUAGE_FILE", tmp_path / "x" / "language")
    assert i18n._read_language() == i18n.PORTUGUESE
    i18n.save_language(i18n.ENGLISH)
    assert i18n._read_language() == i18n.ENGLISH
    i18n.LANGUAGE_FILE.write_text("xx")
    assert i18n._read_language() == i18n.PORTUGUESE


def test_choosing_a_language_saves_it_and_restarts_the_screen(window, tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "LANGUAGE_FILE", tmp_path / "language")
    restarts = []
    monkeypatch.setattr(settingsTab, "restart_screen", lambda: restarts.append(True))
    window.goto(SETTINGS)
    window.settings._set_language(i18n.ENGLISH)
    assert i18n.LANGUAGE_FILE.read_text().strip() == i18n.ENGLISH
    assert restarts == [True]


def test_choosing_the_same_language_does_not_restart(window, monkeypatch):
    restarts = []
    monkeypatch.setattr(settingsTab, "restart_screen", lambda: restarts.append(True))
    window.settings._set_language(i18n.language())
    assert not restarts


def test_english_screen_keeps_every_page_inside_the_screen(qtbot, qapp, api, monkeypatch):
    monkeypatch.setattr(i18n, "_language", i18n.ENGLISH)
    qapp.setStyleSheet(QSS)
    win = MainWindow(ScreenConfig(), api, True)
    qtbot.addWidget(win)
    assert win.minimumSizeHint().height() <= 480
    win.setFixedSize(800, 480)
    win.show()
    qtbot.waitUntil(lambda: win.printer.ready, timeout=2000)
    for index in range(6):
        win.goto(index)
        QtCore.QCoreApplication.processEvents()
        widgets = win.findChildren(QtWidgets.QLabel) + win.findChildren(QtWidgets.QPushButton)
        left = {w.text() for w in widgets if w.text() in i18n.ENGLISH_TEXT}
        assert not left - {"Interior", "Material {}", "Nozzle Align"}, left


@pytest.mark.parametrize("read_only", [False, True])
def test_language_option_is_entirely_on_screen(window, qtbot, read_only):
    window.goto(SETTINGS)
    row = window.settings.language
    qtbot.waitUntil(row.isVisible, timeout=1000)
    bottom = row.mapTo(window, QtCore.QPoint(0, row.height())).y()
    assert bottom <= window.height() - (24 if read_only else 0)
