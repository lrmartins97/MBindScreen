"""Wi-Fi: the network in use, the ones in range, and joining another."""
from __future__ import annotations

from lib.i18n import tr
import logging

from lib import wifi
from lib.panels.networkPage import READ_ONLY_TEXT, is_read_only
from lib.panels.widgets.dialogs import confirm, keyboard
from lib.utils.widgets import ListRow, SubPage, button, clear_layout, label, scroll_column
logger = logging.getLogger(__name__)
WIFI_OFF_WARNING = (
    tr("Desligar o Wi-Fi? Sem cabo de rede, a máquina fica sem Mainsail nem SSH até o "
    "voltares a ligar neste ecrã.")
)
WARNING = (
    tr("Ligar a {ssid}? A máquina pode mudar de endereço, e quem estiver ligado pelo "
    "Mainsail ou por SSH perde a ligação.")
)


def describe(network: wifi.Network, saved: bool) -> str:
    parts = [tr("Sinal {}%", network.signal)]
    parts.append(tr("Protegida") if network.secured else tr("Aberta"))
    if network.in_use:
        parts.append(tr("Ligada"))
    elif saved:
        parts.append(tr("Guardada"))
    return " · ".join(parts)


class WifiPage(SubPage):
    def __init__(self, api, back, nmcli=None) -> None:
        super().__init__("Wi-Fi", back)
        self.api = api
        self.nmcli = nmcli or wifi.Nmcli(self)
        self.networks: list[wifi.Network] = []
        self.profiles: dict[str, str] = {}  # network name -> saved profile
        self.rows: dict[str, ListRow] = {}
        self.address = ""
        self._loading = False
        self._scanning = False
        self._pending: list[str] = []
        self.radio_on = True
        self.radio = button(tr("Desligar Wi-Fi"), self._toggle_radio, height=46)
        self.scan = button(tr("Procurar"), self.refresh, height=46)
        self.head.addWidget(self.radio)
        self.head.addWidget(self.scan)
        self.status = label("", "value")
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.area, self.column = scroll_column(6)
        self.body.addWidget(self.status)
        self.body.addWidget(self.note)
        self.body.addWidget(self.area, 1)

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    # --- reading --------------------------------------------------------
    def refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.status.setText(tr("A procurar redes..."))
        self.nmcli.run(wifi.RADIO, self._on_radio)

    def _unavailable(self) -> None:
        self._loading = False
        self.status.setText(tr("Wi-Fi não disponível"))

    def _on_radio(self, _ok: bool, output: str) -> None:
        self.radio_on = output.strip() != "disabled"
        self.radio.setText(tr("Desligar Wi-Fi") if self.radio_on else tr("Ligar Wi-Fi"))
        self.scan.setVisible(self.radio_on)
        if self.radio_on:
            self.nmcli.run(wifi.DEVICES, self._on_devices)
            return
        self._loading = False
        self.status.setText(tr("Wi-Fi desligado"))
        clear_layout(self.column)
        self.rows = {}

    def _on_devices(self, ok: bool, output: str) -> None:
        device = wifi.find_device(wifi.parse_devices(output) if ok else [], "wifi")
        if device is None:
            self._unavailable()
            return
        self.nmcli.run(wifi.address_args(device.name), self._on_address)

    def _on_address(self, _ok: bool, output: str) -> None:
        self.address = output.strip().split("/")[0]
        self.nmcli.run(wifi.PROFILES, self._on_profiles)

    def _on_profiles(self, ok: bool, output: str) -> None:
        self._pending = wifi.wifi_profiles(output) if ok else []
        self.profiles = {}
        self._next_profile()

    def _next_profile(self) -> None:
        if not self._pending:
            self.nmcli.run(wifi.NETWORKS_KNOWN, self._on_networks)
            return
        name = self._pending.pop()

        def done(ok: bool, output: str) -> None:
            if ok and output.strip():
                self.profiles[output.strip()] = name
            self._next_profile()

        self.nmcli.run(wifi.profile_ssid_args(name), done)

    def _on_networks(self, ok: bool, output: str) -> None:
        """The list appears at once; a scan then completes it."""
        if not ok:
            self._unavailable()
            return
        self._loading = False
        self._show_networks(output)
        if not self._scanning:
            self._scanning = True
            self.scan.setEnabled(False)
            self.nmcli.run(wifi.NETWORKS_FRESH, self._on_scan)

    def _on_scan(self, ok: bool, output: str) -> None:
        self._scanning = False
        self.scan.setEnabled(True)
        if ok and not self._loading and self.radio_on:
            self._show_networks(output)

    def _show_networks(self, output: str) -> None:
        self.networks = wifi.parse_networks(output)
        current = next((n for n in self.networks if n.in_use), None)
        if current:
            self.status.setText(tr("Ligada a {} · {}", current.ssid, self.address))
        else:
            self.status.setText(tr("Sem ligação Wi-Fi"))
        clear_layout(self.column)
        self.rows = {}
        for network in self.networks:
            row = ListRow(
                "wifi", network.ssid, describe(network, network.ssid in self.profiles)
            )
            row.clicked.connect(lambda n=network: self._choose(n))
            self.column.addWidget(row)
            self.rows[network.ssid] = row
        self.column.addStretch()

    # --- changing -------------------------------------------------------
    def _toggle_radio(self) -> None:
        if self._loading:
            return
        if is_read_only(self.api):
            self.note.setText(READ_ONLY_TEXT)
        elif self.radio_on:
            confirm(self, WIFI_OFF_WARNING, lambda: self._set_radio("off"), tr("Desligar"))
        else:
            self._set_radio("on")

    def _set_radio(self, value: str) -> None:
        logger.info("Wi-Fi radio %s", value)
        self.nmcli.run((*wifi.RADIO, value), lambda _ok, _output: self.refresh())

    def _choose(self, network: wifi.Network) -> None:
        if network.in_use or self._loading:
            return
        if is_read_only(self.api):
            self.note.setText(READ_ONLY_TEXT)
            return
        self.note.setText("")
        confirm(self, WARNING.format(ssid=network.ssid), lambda: self._ask(network), tr("Ligar"))

    def _ask(self, network: wifi.Network) -> None:
        profile = self.profiles.get(network.ssid)
        if profile:
            self._join(network.ssid, wifi.join_profile_args(profile))
        elif network.secured:
            keyboard(
                self,
                tr("Palavra-passe de {}", network.ssid),
                lambda password: self._join(network.ssid, wifi.join_args(network.ssid, password)),
                wifi.MINIMUM_PASSWORD,
            )
        else:
            self._join(network.ssid, wifi.join_args(network.ssid))

    def _join(self, ssid: str, args: tuple[str, ...]) -> None:
        logger.info("Joining Wi-Fi network %s", ssid)  # never args: they hold the password
        self._loading = True
        self.status.setText(tr("A ligar a {}...", ssid))
        self.nmcli.run(args, lambda ok, _output: self._joined(ssid, ok))

    def _joined(self, ssid: str, ok: bool) -> None:
        logger.info("Wi-Fi network %s: %s", ssid, "joined" if ok else "failed")
        self._loading = False
        if not ok:
            self.note.setText(
                tr("Não foi possível ligar a {}. Confirma a palavra-passe e o sinal.", ssid)
            )
        self.refresh()

