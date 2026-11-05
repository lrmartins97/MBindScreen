"""Wi-Fi page, with what nmcli really prints on a M-BIND."""
import logging

import pytest
from conftest import click_button, top_dialog
from lib import wifi
from lib.panels.mainWindow import SETTINGS
from lib.panels.wifiPage import READ_ONLY_TEXT

DEVICES = (
    "wlan0:wifi\nlo:loopback\np2p-dev-wlan0:wifi-p2p\neth0:ethernet\n"
)
PROFILES = (
    "netplan-wlan0-BLOCKS:802-11-wireless\nlo:loopback\nnetplan-eth0:802-3-ethernet\n"
    "Pixel_7831:802-11-wireless\n"
)
NETWORKS = (
    "*:BLOCKS:71:WPA2\n :BLOCKS:69:WPA2\n :Pixel_7831:40:WPA2\n :Cafe\\:Livre:55:--\n"
    " :Vizinho:30:WPA2\n : :20:WPA2\n"
)


class FakeNmcli:
    def __init__(self):
        self.calls = []
        self.fail = set()

    def run(self, args, callback):
        self.calls.append(tuple(args))
        key = " ".join(args)
        if "device status" in key:
            answer = DEVICES
        elif "IP4.ADDRESS" in key:
            answer = "192.168.1.172/24\n"
        elif "connection show netplan" in key:
            answer = "BLOCKS\n"
        elif "connection show Pixel" in key:
            answer = "Pixel_7831\n"
        elif "connection show" in key:
            answer = PROFILES
        elif "wifi list" in key:
            answer = NETWORKS
        else:
            answer = ""
        callback(not any(part in key for part in self.fail), answer)


@pytest.fixture
def page(window, qtbot):
    fake = FakeNmcli()
    wifi_page = window.settings.wifi
    wifi_page.nmcli = fake
    window.goto(SETTINGS)
    window.settings.setCurrentWidget(wifi_page)
    qtbot.waitUntil(lambda: bool(wifi_page.rows), timeout=2000)
    wifi_page.fake = fake
    return wifi_page


def test_networks_merge_access_points_and_put_the_current_first():
    networks = wifi.parse_networks(NETWORKS)
    assert [n.ssid for n in networks] == ["BLOCKS", "Cafe:Livre", "Pixel_7831", "Vizinho"]
    assert networks[0].in_use and networks[0].signal == 71
    assert not networks[1].secured


def test_page_shows_the_current_network_and_address(page):
    assert page.status.text() == "Ligada a BLOCKS · 192.168.1.172"
    assert "Ligada" in page.rows["BLOCKS"].description.text()
    assert "Guardada" in page.rows["Pixel_7831"].description.text()
    assert "Aberta" in page.rows["Cafe:Livre"].description.text()


def test_touching_the_current_network_does_nothing(page):
    calls = len(page.fake.calls)
    page.rows["BLOCKS"].clicked.emit()
    assert len(page.fake.calls) == calls


def test_a_saved_network_joins_with_its_profile_after_a_warning(page, window):
    page.rows["Pixel_7831"].clicked.emit()
    assert not any("up" in call for call in page.fake.calls)
    click_button(top_dialog(window), "Ligar")
    assert ("connection", "up", "Pixel_7831") in page.fake.calls


def test_an_open_network_needs_no_password(page, window):
    page.rows["Cafe:Livre"].clicked.emit()
    click_button(top_dialog(window), "Ligar")
    assert ("device", "wifi", "connect", "Cafe:Livre") in page.fake.calls


def type_password(window, text):
    dialog = top_dialog(window)
    for char in text:
        click_button(dialog, char)
    click_button(dialog, "Ligar")


def test_new_network_asks_for_the_password_and_never_logs_it(page, window, caplog):
    caplog.set_level(logging.DEBUG)
    page.rows["Vizinho"].clicked.emit()
    click_button(top_dialog(window), "Ligar")
    type_password(window, "segredo123")
    assert wifi.join_args("Vizinho", "segredo123") in page.fake.calls
    assert "Vizinho" in caplog.text and "segredo123" not in caplog.text


def test_failure_to_join_is_explained_and_the_list_comes_back(page, window):
    page.fake.fail.add("Cafe")
    page.rows["Cafe:Livre"].clicked.emit()
    click_button(top_dialog(window), "Ligar")
    assert "Não foi possível ligar a Cafe:Livre" in page.note.text()
    assert page.status.text().startswith("Ligada a BLOCKS")


def test_read_only_trial_never_changes_the_network(page, api):
    api.read_only = True
    page.rows["Vizinho"].clicked.emit()
    assert page.note.text() == READ_ONLY_TEXT
    assert not any("connect" in call for call in page.fake.calls)


def test_machine_without_wifi_says_so(page):
    page.fake.fail.add("device status")
    page.refresh()
    assert page.status.text() == "Wi-Fi não disponível"
