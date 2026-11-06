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


STATUS = (
    '{"BackendState": "Running", "Self": {"TailscaleIPs": ["100.64.0.9", "fd7a::9"], '
    '"Online": true}}'
)


class FakeTailscale:
    def __init__(self):
        self.calls = []
        self.output = STATUS
        self.ok = True

    def run(self, args, callback, program="nmcli"):
        self.calls.append((program, *args))
        callback(self.ok, self.output if args[0] == "status" else "")


@pytest.fixture
def remote(tab):
    tab.remote.nmcli = FakeTailscale()
    tab.setCurrentWidget(tab.remote)
    return tab.remote


def test_tailscale_only_appears_with_developer_mode(tab, window):
    assert tab.network.remote.isHidden()
    enter(window, CODE)
    assert not tab.network.remote.isHidden()
    tab.developer.clicked.emit()
    assert tab.network.remote.isHidden()


def test_tailscale_shows_its_state_and_address(remote):
    assert remote.status.text() == "Ligado · 100.64.0.9"
    assert remote.toggle.text() == "Desligar"


def test_turning_tailscale_off_warns_first(remote, window):
    remote.toggle.click()
    assert ("tailscale", "down") not in remote.nmcli.calls
    click_button(top_dialog(window), "Desligar")
    assert ("tailscale", "down") in remote.nmcli.calls


def test_turning_tailscale_on_needs_no_warning(remote):
    remote.nmcli.output = '{"BackendState": "Stopped", "Self": {}}'
    remote.refresh()
    assert remote.status.text() == "Desligado"
    remote.toggle.click()
    assert ("tailscale", "up") in remote.nmcli.calls


def test_refused_change_says_what_to_authorise(remote, window):
    remote.nmcli.ok = False
    remote.toggle.click()
    click_button(top_dialog(window), "Desligar")
    assert "--operator" in remote.note.text()


def test_machine_without_tailscale_says_so(remote):
    remote.nmcli.output = ""
    remote.refresh()
    assert remote.status.text() == "Tailscale não disponível"
    assert not remote.toggle.isEnabled()


def test_read_only_trial_does_not_touch_tailscale(remote, api):
    api.read_only = True
    remote.toggle.click()
    assert ("tailscale", "up") not in remote.nmcli.calls
    assert ("tailscale", "down") not in remote.nmcli.calls
