"""Wi-Fi: the network in use, the ones in range, and joining another."""
from __future__ import annotations

import logging

from lib import wifi
from lib.panels.widgets.dialogs import confirm, keyboard
from lib.utils.widgets import ListRow, SubPage, button, clear_layout, label, scroll_column
logger = logging.getLogger(__name__)
READ_ONLY_TEXT = "No modo de experiência só leitura não se muda de rede."
WARNING = (
    "Ligar a {ssid}? A máquina pode mudar de endereço, e quem estiver ligado pelo "
    "Mainsail ou por SSH perde a ligação."
)


def describe(network: wifi.Network, saved: bool) -> str:
    parts = [f"Sinal {network.signal}%"]
    parts.append("Protegida" if network.secured else "Aberta")
    if network.in_use:
        parts.append("Ligada")
    elif saved:
        parts.append("Guardada")
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
        self._pending: list[str] = []
        self.scan = button("Procurar", self.refresh, height=46)
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
        self.status.setText("A procurar redes...")
        self.nmcli.run(wifi.DEVICES, self._on_devices)

    def _unavailable(self) -> None:
        self._loading = False
        self.status.setText("Wi-Fi não disponível")

    def _on_devices(self, ok: bool, output: str) -> None:
        device = wifi.wifi_device(output) if ok else None
        if device is None:
            self._unavailable()
            return
        self.nmcli.run(wifi.address_args(device), self._on_address)

    def _on_address(self, _ok: bool, output: str) -> None:
        self.address = output.strip().split("/")[0]
        self.nmcli.run(wifi.PROFILES, self._on_profiles)

    def _on_profiles(self, ok: bool, output: str) -> None:
        self._pending = wifi.wifi_profiles(output) if ok else []
        self.profiles = {}
        self._next_profile()

    def _next_profile(self) -> None:
        if not self._pending:
            self.nmcli.run(wifi.NETWORKS, self._on_networks)
            return
        name = self._pending.pop()

        def done(ok: bool, output: str) -> None:
            if ok and output.strip():
                self.profiles[output.strip()] = name
            self._next_profile()

        self.nmcli.run(wifi.profile_ssid_args(name), done)

    def _on_networks(self, ok: bool, output: str) -> None:
        if not ok:
            self._unavailable()
            return
        self._loading = False
        self.networks = wifi.parse_networks(output)
        current = next((n for n in self.networks if n.in_use), None)
        if current:
            self.status.setText(f"Ligada a {current.ssid} · {self.address}")
        else:
            self.status.setText("Sem ligação Wi-Fi")
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

    # --- joining --------------------------------------------------------
    def _choose(self, network: wifi.Network) -> None:
        if network.in_use or self._loading:
            return
        if getattr(self.api, "read_only", False):
            self.note.setText(READ_ONLY_TEXT)
            return
        self.note.setText("")
        confirm(self, WARNING.format(ssid=network.ssid), lambda: self._ask(network), "Ligar")

    def _ask(self, network: wifi.Network) -> None:
        profile = self.profiles.get(network.ssid)
        if profile:
            self._join(network.ssid, wifi.join_profile_args(profile))
        elif network.secured:
            keyboard(
                self,
                f"Palavra-passe de {network.ssid}",
                lambda password: self._join(network.ssid, wifi.join_args(network.ssid, password)),
                wifi.MINIMUM_PASSWORD,
            )
        else:
            self._join(network.ssid, wifi.join_args(network.ssid))

    def _join(self, ssid: str, args: tuple[str, ...]) -> None:
        logger.info("Joining Wi-Fi network %s", ssid)  # never args: they hold the password
        self._loading = True
        self.status.setText(f"A ligar a {ssid}...")
        self.nmcli.run(args, lambda ok, _output: self._joined(ssid, ok))

    def _joined(self, ssid: str, ok: bool) -> None:
        logger.info("Wi-Fi network %s: %s", ssid, "joined" if ok else "failed")
        self._loading = False
        if not ok:
            self.note.setText(
                f"Não foi possível ligar a {ssid}. Confirma a palavra-passe e o sinal."
            )
        self.refresh()

