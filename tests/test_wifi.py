"""Wi-Fi page: nmcli output in its real format, with invented names."""
import logging

import pytest
from conftest import click_button, top_dialog
from lib import wifi
from lib.panels.mainWindow import SETTINGS
from lib.panels.networkPage import READ_ONLY_TEXT
from PyQt6.QtWidgets import QLabel

DEVICES = (
    "wlan0:wifi:connected:perfil-oficina\nlo:loopback:connected (externally):lo\n"
    "p2p-dev-wlan0:wifi-p2p:disconnected:\neth0:ethernet:unavailable:\n"
)
PROFILES = (
    "perfil-oficina:802-11-wireless\nlo:loopback\nperfil-cabo:802-3-ethernet\n"
    "Telefone:802-11-wireless\n"
)
NETWORKS = (
    "*:Oficina:71:WPA2\n :Oficina:69:WPA2\n :Telefone:40:WPA2\n :Cafe\\:Livre:55:--\n"
    " :Vizinho:30:WPA2\n : :20:WPA2\n"
)


class FakeNmcli:
    def __init__(self):
        self.calls = []
        self.fail = set()
        self.devices = DEVICES
        self.radio = "enabled\n"
        self.hotspot_name = ""

    def run(self, args, callback):
        self.calls.append(tuple(args))
        key = " ".join(args)
        if key == "radio wifi":
            answer = self.radio
        elif "device status" in key:
            answer = self.devices
        elif "show MBind-hotspot" in key:
            answer = self.hotspot_name
        elif "IP4.ADDRESS" in key:
            answer = "192.0.2.10/24\n"
        elif "connection show perfil-oficina" in key:
            answer = "Oficina\n"
        elif "connection show Telefone" in key:
            answer = "Telefone\n"
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
    assert [n.ssid for n in networks] == ["Oficina", "Cafe:Livre", "Telefone", "Vizinho"]
    assert networks[0].in_use and networks[0].signal == 71
    assert not networks[1].secured


def test_page_shows_the_current_network_and_address(page):
    assert page.status.text() == "Ligada a Oficina · 192.0.2.10"
    assert "Ligada" in page.rows["Oficina"].description.text()
    assert "Guardada" in page.rows["Telefone"].description.text()
    assert "Aberta" in page.rows["Cafe:Livre"].description.text()


def test_touching_the_current_network_does_nothing(page):
    calls = len(page.fake.calls)
    page.rows["Oficina"].clicked.emit()
    assert len(page.fake.calls) == calls


def test_a_saved_network_joins_with_its_profile_after_a_warning(page, window):
    page.rows["Telefone"].clicked.emit()
    assert not any("up" in call for call in page.fake.calls)
    click_button(top_dialog(window), "Ligar")
    assert ("connection", "up", "Telefone") in page.fake.calls


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
    assert page.status.text().startswith("Ligada a Oficina")


def test_read_only_trial_never_changes_the_network(page, api):
    api.read_only = True
    page.rows["Vizinho"].clicked.emit()
    assert page.note.text() == READ_ONLY_TEXT
    assert not any("connect" in call for call in page.fake.calls)


def test_machine_without_wifi_says_so(page):
    page.fake.fail.add("device status")
    page.refresh()
    assert page.status.text() == "Wi-Fi não disponível"


def test_turning_wifi_off_warns_and_the_page_says_it_is_off(page, window):
    page.radio.click()
    assert not any(call[:2] == ("radio", "wifi") and len(call) == 3 for call in page.fake.calls)
    page.fake.radio = "disabled\n"
    click_button(top_dialog(window), "Desligar")
    assert ("radio", "wifi", "off") in page.fake.calls
    assert page.status.text() == "Wi-Fi desligado"
    page.radio.click()  # coming back needs no warning
    assert ("radio", "wifi", "on") in page.fake.calls


@pytest.fixture
def network(window, qtbot):
    fake = FakeNmcli()
    tab = window.settings
    tab.network.nmcli = tab.wifi.nmcli = tab.hotspot.nmcli = fake
    window.goto(SETTINGS)
    tab.setCurrentWidget(tab.network)
    tab.fake = fake
    return tab


def test_network_page_shows_the_three_connections(network):
    assert network.network.ethernet.description.text() == "Sem cabo"
    assert network.network.wifi.description.text() == "Ligado · 192.0.2.10"
    assert network.network.hotspot.description.text() == "Desligado"


def test_network_rows_open_their_pages(network):
    network.network.wifi.clicked.emit()
    assert network.currentWidget() is network.wifi
    network.setCurrentWidget(network.network)
    network.network.hotspot.clicked.emit()
    assert network.currentWidget() is network.hotspot


def test_ethernet_without_a_cable_has_no_action(network):
    calls = len(network.fake.calls)
    network.network.ethernet.clicked.emit()
    assert len(network.fake.calls) == calls


def test_ethernet_with_a_cable_connects_after_asking(network, window):
    network.fake.devices = DEVICES.replace("eth0:ethernet:unavailable:", "eth0:ethernet:disconnected:")
    network.network.refresh()
    assert network.network.ethernet.description.text() == "Cabo ligado, sem rede"
    network.network.ethernet.clicked.emit()
    click_button(top_dialog(window), "Confirmar")
    assert ("device", "connect", "eth0") in network.fake.calls


def open_hotspot(network):
    network.setCurrentWidget(network.hotspot)
    return network.hotspot


def fill(window, text, then):
    dialog = top_dialog(window)
    for _ in range(len(next(c for c in dialog.findChildren(QLabel) if c.objectName() == "display").text().strip())):
        click_button(dialog, "⌫")
    for char in text:
        click_button(dialog, char)
    click_button(dialog, then)


def test_first_hotspot_asks_name_and_password_and_keeps_them_out_of_the_log(
    network, window, caplog
):
    caplog.set_level(logging.DEBUG)
    hotspot = open_hotspot(network)
    assert hotspot.status.text() == "Por configurar"
    hotspot.toggle.click()
    fill(window, "mbind", "Seguinte")
    fill(window, "segredo123", "Seguinte")
    click_button(top_dialog(window), "Ativar")
    assert wifi.hotspot_args("wlan0", "mbind", "segredo123") in network.fake.calls
    assert "segredo123" not in caplog.text


def test_saved_hotspot_starts_with_a_warning_and_stops(network, window):
    network.fake.hotspot_name = "M-BIND\n"
    hotspot = open_hotspot(network)
    assert hotspot.status.text() == "Desligado: M-BIND"
    hotspot.toggle.click()
    click_button(top_dialog(window), "Ativar")
    assert ("connection", "up", wifi.HOTSPOT) in network.fake.calls
    network.fake.devices = DEVICES.replace("perfil-oficina", wifi.HOTSPOT)
    hotspot.refresh()
    assert hotspot.status.text().startswith("Ativo: M-BIND")
    assert network.network.hotspot.isEnabled()
    hotspot.toggle.click()
    click_button(top_dialog(window), "Desativar")
    assert ("connection", "down", wifi.HOTSPOT) in network.fake.calls


def test_changing_a_saved_hotspot_replaces_the_profile(network, window):
    network.fake.hotspot_name = "M-BIND\n"
    hotspot = open_hotspot(network)
    hotspot.change.click()
    fill(window, "novo", "Seguinte")
    fill(window, "segredo123", "Seguinte")
    click_button(top_dialog(window), "Ativar")
    calls = network.fake.calls
    delete = calls.index(("connection", "delete", wifi.HOTSPOT))
    assert calls.index(wifi.hotspot_args("wlan0", "novo", "segredo123")) > delete


def test_read_only_trial_touches_neither_hotspot_nor_radio(network, api):
    api.read_only = True
    hotspot = open_hotspot(network)
    hotspot.toggle.click()
    hotspot.change.click()
    assert hotspot.note.text() == READ_ONLY_TEXT
    network.setCurrentWidget(network.wifi)
    network.wifi.radio.click()
    assert not any(call[:1] == ("radio",) and len(call) == 3 for call in network.fake.calls)
