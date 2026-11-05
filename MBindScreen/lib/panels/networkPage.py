"""Network, organised like BlocksScreen: Ethernet, Wi-Fi and hotspot."""
from __future__ import annotations

import logging

from lib import wifi
from lib.panels.widgets.dialogs import confirm, keyboard
from lib.utils.widgets import ListRow, SubPage, button, label

logger = logging.getLogger(__name__)
READ_ONLY_TEXT = "No modo de experiência só leitura não se muda a rede."
DEFAULT_HOTSPOT_NAME = "M-BIND"
HOTSPOT_WARNING = (
    "Ativar o hotspot? O Wi-Fi deixa a rede atual, e quem estiver ligado pelo Mainsail "
    "ou por SSH perde a ligação."
)
HOTSPOT_OFF_WARNING = "Desativar o hotspot? Quem estiver ligado a ele perde a ligação."


def is_read_only(api) -> bool:
    return bool(getattr(api, "read_only", False))


def ethernet_text(device, address: str) -> str:
    if device is None:
        return "Sem placa de rede"
    if device.state == "connected":
        return f"Ligada · {address}"
    return "Sem cabo" if device.state == "unavailable" else "Cabo ligado, sem rede"


def wifi_text(device, address: str) -> str:
    if device is None:
        return "Sem Wi-Fi"
    if device.connection == wifi.HOTSPOT:
        return "Em uso pelo hotspot"
    if device.state == "connected":
        return f"Ligado · {address}"
    return "Desligado" if device.state == "unavailable" else "Sem ligação"


class NetworkPage(SubPage):
    def __init__(self, api, open_wifi, open_hotspot, back, nmcli=None) -> None:
        super().__init__("Rede", back)
        self.api = api
        self.nmcli = nmcli or wifi.Nmcli(self)
        self.ethernet_device = None
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.ethernet = ListRow("ethernet", "Ethernet", "A ler...")
        self.wifi = ListRow("wifi", "Wi-Fi", "A ler...")
        self.hotspot = ListRow("hotspot", "Hotspot", "A ler...")
        self.ethernet.clicked.connect(self._ethernet_action)
        self.wifi.clicked.connect(open_wifi)
        self.hotspot.clicked.connect(open_hotspot)
        for row in (self.ethernet, self.wifi, self.hotspot):
            self.body.addWidget(row)
        self.body.addWidget(self.note)
        self.body.addStretch()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self.nmcli.run(wifi.DEVICES, self._on_devices)

    def _with_address(self, device, show) -> None:
        if device is None or device.state != "connected":
            show("")
            return
        self.nmcli.run(
            wifi.address_args(device.name),
            lambda _ok, output: show(output.strip().split("/")[0]),
        )

    def _on_devices(self, ok: bool, output: str) -> None:
        devices = wifi.parse_devices(output) if ok else []
        ethernet = wifi.find_device(devices, "ethernet")
        radio = wifi.find_device(devices, "wifi")
        self.ethernet_device = ethernet
        self._with_address(
            ethernet, lambda a: self.ethernet.description.setText(ethernet_text(ethernet, a))
        )
        self._with_address(radio, lambda a: self.wifi.description.setText(wifi_text(radio, a)))
        hotspot_on = radio is not None and radio.connection == wifi.HOTSPOT
        self._with_address(
            radio if hotspot_on else None,
            lambda a: self.hotspot.description.setText(
                f"Ativo · {a}" if hotspot_on else "Desligado"
            ),
        )

    def _ethernet_action(self) -> None:
        device = self.ethernet_device
        if device is None or device.state == "unavailable":
            return
        if is_read_only(self.api):
            self.note.setText(READ_ONLY_TEXT)
            return
        connected = device.state == "connected"
        verb = "disconnect" if connected else "connect"
        text = "Desligar a Ethernet?" if connected else "Ligar a Ethernet?"
        confirm(self, text, lambda: self._run_ethernet(verb, device.name), "Confirmar")

    def _run_ethernet(self, verb: str, name: str) -> None:
        def done(ok: bool, _output: str) -> None:
            self.note.setText("" if ok else "Não foi possível mudar a Ethernet.")
            self.refresh()

        self.nmcli.run(("device", verb, name), done)


class HotspotPage(SubPage):
    """The machine makes its own network. The name and password live in NetworkManager."""

    def __init__(self, api, back, nmcli=None) -> None:
        super().__init__("Hotspot", back)
        self.api = api
        self.nmcli = nmcli or wifi.Nmcli(self)
        self.active = False
        self.saved = False
        self.name = ""
        self.device = ""
        self.status = label("", "value")
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.toggle = button("Ativar", self._toggle, "accent", 58)
        self.change = button("Mudar nome e palavra-passe", self._change, height=52)
        for widget in (self.status, self.note, self.toggle, self.change):
            self.body.addWidget(widget)
        self.body.addStretch()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self.status.setText("A ler...")
        self.nmcli.run(wifi.DEVICES, self._on_devices)

    def _on_devices(self, ok: bool, output: str) -> None:
        radio = wifi.find_device(wifi.parse_devices(output) if ok else [], "wifi")
        self.device = radio.name if radio else ""
        self.active = radio is not None and radio.connection == wifi.HOTSPOT
        self.toggle.setEnabled(radio is not None)
        self.change.setEnabled(radio is not None)
        self.toggle.setText("Desativar" if self.active else "Ativar")
        self.nmcli.run(wifi.profile_ssid_args(wifi.HOTSPOT), self._on_profile)

    def _on_profile(self, ok: bool, output: str) -> None:
        self.saved = ok and bool(output.strip())
        self.name = output.strip() if self.saved else ""
        if not self.device:
            self.status.setText("Sem Wi-Fi")
        elif not self.saved:
            self.status.setText("Por configurar")
        elif self.active:
            self.status.setText(f"Ativo: {self.name}")
        else:
            self.status.setText(f"Desligado: {self.name}")
        if self.active:
            self.nmcli.run(wifi.address_args(self.device), self._on_address)

    def _on_address(self, _ok: bool, output: str) -> None:
        address = output.strip().split("/")[0]
        if address:
            self.status.setText(f"Ativo: {self.name} · {address}")

    def _allowed(self) -> bool:
        if is_read_only(self.api):
            self.note.setText(READ_ONLY_TEXT)
            return False
        self.note.setText("")
        return True

    def _toggle(self) -> None:
        if not self._allowed():
            return
        if self.active:
            confirm(
                self,
                HOTSPOT_OFF_WARNING,
                lambda: self._run(("connection", "down", wifi.HOTSPOT), "desativar"),
                "Desativar",
            )
        elif self.saved:
            confirm(
                self,
                HOTSPOT_WARNING,
                lambda: self._run(("connection", "up", wifi.HOTSPOT), "ativar"),
                "Ativar",
            )
        else:
            self._change()

    def _change(self) -> None:
        if not self._allowed():
            return
        keyboard(
            self,
            "Nome do hotspot",
            self._ask_password,
            1,
            "Seguinte",
            self.name or DEFAULT_HOTSPOT_NAME,
        )

    def _ask_password(self, name: str) -> None:
        keyboard(
            self,
            f"Palavra-passe de {name}",
            lambda password: confirm(
                self, HOTSPOT_WARNING, lambda: self._create(name, password), "Ativar"
            ),
            wifi.MINIMUM_PASSWORD,
            "Seguinte",
        )

    def _create(self, name: str, password: str) -> None:
        create = wifi.hotspot_args(self.device, name, password)
        if self.saved:
            self.nmcli.run(
                ("connection", "delete", wifi.HOTSPOT),
                lambda _ok, _output: self._run(create, "ativar"),
            )
        else:
            self._run(create, "ativar")

    def _run(self, args: tuple[str, ...], action: str) -> None:
        logger.info("Hotspot: %s", action)  # never args: they may hold the password
        self.status.setText("A aguardar...")

        def done(ok: bool, _output: str) -> None:
            self.note.setText("" if ok else f"Não foi possível {action} o hotspot.")
            self.refresh()

        self.nmcli.run(args, done)
