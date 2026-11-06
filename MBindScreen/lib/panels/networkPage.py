"""Network, organised like BlocksScreen: Ethernet, Wi-Fi and hotspot."""
from __future__ import annotations

from lib.i18n import tr
import logging

from lib import wifi
from lib.panels.widgets.dialogs import confirm, keyboard
from lib.utils.widgets import ListRow, SubPage, button, label

logger = logging.getLogger(__name__)
READ_ONLY_TEXT = tr("No modo de experiência só leitura não se muda a rede.")
DEFAULT_HOTSPOT_NAME = "M-BIND"
HOTSPOT_WARNING = (
    tr("Ativar o hotspot? O Wi-Fi deixa a rede atual, e quem estiver ligado pelo Mainsail "
    "ou por SSH perde a ligação.")
)
START_FAILED = tr("Não foi possível ativar o hotspot.")
STOP_FAILED = tr("Não foi possível desativar o hotspot.")
HOTSPOT_OFF_WARNING = tr("Desativar o hotspot? Quem estiver ligado a ele perde a ligação.")


def is_read_only(api) -> bool:
    return bool(getattr(api, "read_only", False))


def ethernet_text(device, address: str) -> str:
    if device is None:
        return tr("Sem placa de rede")
    if device.state == "connected":
        return tr("Ligada · {}", address)
    return tr("Sem cabo") if device.state == "unavailable" else tr("Cabo ligado, sem rede")


def wifi_text(device, address: str) -> str:
    if device is None:
        return tr("Sem Wi-Fi")
    if device.connection == wifi.HOTSPOT:
        return tr("Em uso pelo hotspot")
    if device.state == "connected":
        return tr("Ligado · {}", address)
    return tr("Desligado") if device.state == "unavailable" else tr("Sem ligação")


class NetworkPage(SubPage):
    def __init__(self, api, open_wifi, open_hotspot, open_remote, back, nmcli=None) -> None:
        super().__init__(tr("Rede"), back)
        self.api = api
        self.nmcli = nmcli or wifi.Nmcli(self)
        self.ethernet_device = None
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.ethernet = ListRow("ethernet", "Ethernet", tr("A ler..."))
        self.wifi = ListRow("wifi", "Wi-Fi", tr("A ler..."))
        self.hotspot = ListRow("hotspot", "Hotspot", tr("A ler..."))
        self.remote = ListRow("remote", "Tailscale", tr("Acesso remoto."))
        self.remote.clicked.connect(open_remote)
        self.remote.hide()  # developer mode only
        self.ethernet.clicked.connect(self._ethernet_action)
        self.wifi.clicked.connect(open_wifi)
        self.hotspot.clicked.connect(open_hotspot)
        for row in (self.ethernet, self.wifi, self.hotspot, self.remote):
            self.body.addWidget(row)
        self.body.addWidget(self.note)
        self.body.addStretch()

    def set_developer(self, on: bool) -> None:
        self.remote.setVisible(on)

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
                tr("Ativo · {}", a) if hotspot_on else tr("Desligado")
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
        text = tr("Desligar a Ethernet?") if connected else tr("Ligar a Ethernet?")
        confirm(self, text, lambda: self._run_ethernet(verb, device.name), tr("Confirmar"))

    def _run_ethernet(self, verb: str, name: str) -> None:
        def done(ok: bool, _output: str) -> None:
            self.note.setText("" if ok else tr("Não foi possível mudar a Ethernet."))
            self.refresh()

        self.nmcli.run(("device", verb, name), done)


class RemotePage(SubPage):
    """Tailscale, for the people who look after the machine, not for its everyday user."""

    def __init__(self, api, back, nmcli=None) -> None:
        super().__init__("Tailscale", back)
        self.api = api
        self.nmcli = nmcli or wifi.Nmcli(self)
        self.access = None
        self.status = label("", "value")
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.toggle = button(tr("Ligar"), self._toggle, "accent", 58)
        for widget in (self.status, self.note, self.toggle):
            self.body.addWidget(widget)
        self.body.addStretch()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self.status.setText(tr("A ler..."))
        self.nmcli.run(wifi.TAILSCALE_STATUS, self._on_status, wifi.TAILSCALE)

    def _on_status(self, _ok: bool, output: str) -> None:
        self.access = wifi.parse_tailscale(output)
        self.toggle.setEnabled(self.access is not None)
        if self.access is None:
            self.status.setText(tr("Tailscale não disponível"))
            return
        on = self.access.state == wifi.TAILSCALE_ON
        self.toggle.setText(tr("Desligar") if on else tr("Ligar"))
        self.status.setText(
            tr("Ligado · {}", self.access.address) if on
            else tr("Desligado") if self.access.state == "Stopped"
            else tr("Por autenticar")
        )

    def _toggle(self) -> None:
        if is_read_only(self.api):
            self.note.setText(READ_ONLY_TEXT)
            return
        self.note.setText("")
        if self.access is not None and self.access.state == wifi.TAILSCALE_ON:
            confirm(
                self,
                tr("Desligar o Tailscale? Perde-se o acesso remoto a esta máquina."),
                lambda: self._run("down"),
                tr("Desligar"),
            )
        else:
            self._run("up")

    def _run(self, verb: str) -> None:
        logger.info("Tailscale %s", verb)

        def done(ok: bool, _output: str) -> None:
            if not ok:
                self.note.setText(tr(
                    "Não foi possível. Sem password, é preciso autorizar uma vez por SSH: "
                    "sudo tailscale set --operator=$USER"
                ))
            self.refresh()

        self.nmcli.run((verb,), done, wifi.TAILSCALE)


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
        self.toggle = button(tr("Ativar"), self._toggle, "accent", 58)
        self.change = button(tr("Mudar nome e palavra-passe"), self._change, height=52)
        for widget in (self.status, self.note, self.toggle, self.change):
            self.body.addWidget(widget)
        self.body.addStretch()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self.status.setText(tr("A ler..."))
        self.nmcli.run(wifi.DEVICES, self._on_devices)

    def _on_devices(self, ok: bool, output: str) -> None:
        radio = wifi.find_device(wifi.parse_devices(output) if ok else [], "wifi")
        self.device = radio.name if radio else ""
        self.active = radio is not None and radio.connection == wifi.HOTSPOT
        self.toggle.setEnabled(radio is not None)
        self.change.setEnabled(radio is not None)
        self.toggle.setText(tr("Desativar") if self.active else tr("Ativar"))
        self.nmcli.run(wifi.profile_ssid_args(wifi.HOTSPOT), self._on_profile)

    def _on_profile(self, ok: bool, output: str) -> None:
        self.saved = ok and bool(output.strip())
        self.name = output.strip() if self.saved else ""
        if not self.device:
            self.status.setText(tr("Sem Wi-Fi"))
        elif not self.saved:
            self.status.setText(tr("Por configurar"))
        elif self.active:
            self.status.setText(tr("Ativo: {}", self.name))
        else:
            self.status.setText(tr("Desligado: {}", self.name))
        if self.active:
            self.nmcli.run(wifi.address_args(self.device), self._on_address)

    def _on_address(self, _ok: bool, output: str) -> None:
        address = output.strip().split("/")[0]
        if address:
            self.status.setText(tr("Ativo: {} · {}", self.name, address))

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
                lambda: self._run(("connection", "down", wifi.HOTSPOT), STOP_FAILED),
                tr("Desativar"),
            )
        elif self.saved:
            confirm(
                self,
                HOTSPOT_WARNING,
                lambda: self._run(("connection", "up", wifi.HOTSPOT), START_FAILED),
                tr("Ativar"),
            )
        else:
            self._change()

    def _change(self) -> None:
        if not self._allowed():
            return
        keyboard(
            self,
            tr("Nome do hotspot"),
            self._ask_password,
            1,
            tr("Seguinte"),
            self.name or DEFAULT_HOTSPOT_NAME,
        )

    def _ask_password(self, name: str) -> None:
        keyboard(
            self,
            tr("Palavra-passe de {}", name),
            lambda password: confirm(
                self, HOTSPOT_WARNING, lambda: self._create(name, password), tr("Ativar")
            ),
            wifi.MINIMUM_PASSWORD,
            tr("Seguinte"),
        )

    def _create(self, name: str, password: str) -> None:
        create = wifi.hotspot_args(self.device, name, password)
        if self.saved:
            self.nmcli.run(
                ("connection", "delete", wifi.HOTSPOT),
                lambda _ok, _output: self._run(create, START_FAILED),
            )
        else:
            self._run(create, START_FAILED)

    def _run(self, args: tuple[str, ...], failure: str) -> None:
        logger.info("Hotspot: %s", args[0:2])  # never all of it: it may hold the password
        self.status.setText(tr("A aguardar..."))

        def done(ok: bool, _output: str) -> None:
            self.note.setText("" if ok else failure)
            self.refresh()

        self.nmcli.run(args, done)
