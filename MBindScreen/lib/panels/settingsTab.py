"""Settings: messages, system, updates, screen switch and restarts."""
from __future__ import annotations

from lib.i18n import tr
import datetime
import logging
import os
import sys

from lib import screenSwitch
from lib import i18n
from lib.panels.widgets.dialogs import choose, confirm
from lib.panels.networkPage import HotspotPage, NetworkPage
from lib.panels.wifiPage import WifiPage
from lib.utils.theme import ACCENT, DIM, RED
from lib.utils.widgets import (
    ListRow,
    SubPage,
    button,
    card,
    clear_layout,
    label,
    scroll_column,
)
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)
OWN_UPDATE_NAME = "MBindScreen"
MENU_COLUMNS = 2


def update_available(entry: dict) -> bool:
    if "commits_behind" in entry:
        return bool(entry["commits_behind"])
    version, remote = entry.get("version"), entry.get("remote_version")
    return bool(version and remote and "?" not in (version, remote) and version != remote)


class MessagesPage(SubPage):
    """Errors first, then the last console lines."""

    def __init__(self, printer, back) -> None:
        super().__init__(tr("Mensagens"), back)
        self.printer = printer
        self.head.addWidget(button(tr("Limpar avisos"), printer.clear_alerts, height=46))
        self.area, self.column = scroll_column(4)
        self.body.addWidget(self.area, 1)
        printer.console_line.connect(lambda _line: self.refresh())
        printer.updated.connect(self._alerts_changed)
        self._alert_count = 0

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def _alerts_changed(self) -> None:
        if len(self.printer.alerts) != self._alert_count:
            self.refresh()

    def _line(self, when: float, text: str, color: str) -> None:
        stamp = datetime.datetime.fromtimestamp(when).strftime("%H:%M:%S")
        widget = label(f"{stamp}  {text}")
        widget.setWordWrap(True)
        widget.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.column.addWidget(widget)

    def refresh(self) -> None:
        self._alert_count = len(self.printer.alerts)
        if not self.isVisible():
            return
        clear_layout(self.column)
        for when, text in reversed(self.printer.alerts):
            self._line(when, text, RED)
        for when, text in reversed(self.printer.console):
            if not text.startswith("!!"):
                self._line(when, text.removeprefix("//").strip(), DIM)
        self.column.addStretch()


class SystemPage(SubPage):
    def __init__(self, api, back) -> None:
        super().__init__(tr("Sistema"), back)
        self.api = api
        frame, self.column = card(16, 6)
        self.body.addWidget(frame)
        self.body.addStretch()

    def showEvent(self, event) -> None:
        clear_layout(self.column)
        self.api.call("printer.info", None, self._printer_info)
        self.api.call("machine.system_info", None, self._system_info)
        super().showEvent(event)

    def _row(self, title: str, value: str) -> None:
        row = QtWidgets.QHBoxLayout()
        row.addWidget(label(title, "dim"))
        row.addStretch()
        row.addWidget(label(value))
        self.column.addLayout(row)

    def _printer_info(self, result, _error) -> None:
        if result:
            self._row(tr("Nome"), str(result.get("hostname", "—")))
            self._row("Klipper", str(result.get("software_version", "—")))

    def _system_info(self, result, _error) -> None:
        info = (result or {}).get("system_info", {})
        distribution = info.get("distribution", {}).get("name")
        if distribution:
            self._row(tr("Sistema"), distribution)
        for name, interface in info.get("network", {}).items():
            addresses = [
                a["address"]
                for a in interface.get("ip_addresses", [])
                if a.get("family") == "ipv4"
            ]
            if addresses:
                self._row(name, ", ".join(addresses))


class UpdatesPage(SubPage):
    """Update state of everything Moonraker manages; only this screen updates here."""

    def __init__(self, printer, api, back) -> None:
        super().__init__(tr("Atualizações"), back)
        self.printer, self.api = printer, api
        self.head.addWidget(button(tr("Verificar"), self._check, height=46))
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)
        self.area, self.column = scroll_column(6)
        self.body.addWidget(self.area, 1)

    def showEvent(self, event) -> None:
        self._load()
        super().showEvent(event)

    def _load(self) -> None:
        self.api.call("machine.update.status", None, self._loaded)

    def _check(self) -> None:
        self.note.setText(tr("A verificar…"))
        self.api.call("machine.update.refresh", None, self._refreshed)

    def _refreshed(self, _result, error) -> None:
        text = ""
        if error:
            text = error.get("message", tr("Falhou")) if isinstance(error, dict) else str(error)
        self.note.setText(text)
        self._load()

    def _loaded(self, result, _error) -> None:
        clear_layout(self.column)
        for name, entry in sorted(((result or {}).get("version_info") or {}).items()):
            if name == "system":
                continue
            self.column.addWidget(self._row(name, entry))
        self.column.addStretch()

    def _row(self, name: str, entry: dict) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setObjectName("card")
        row = QtWidgets.QHBoxLayout(frame)
        row.setContentsMargins(14, 8, 14, 8)
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(0)
        column.addWidget(label(name, "value"))
        version = entry.get("full_version_string") or entry.get("version") or "?"
        column.addWidget(label(str(version), "dim"))
        row.addLayout(column, 1)
        available = update_available(entry)
        if name == OWN_UPDATE_NAME and available:
            row.addWidget(button(tr("Atualizar"), self._update_self, "accent", 46))
        else:
            state = label(tr("Atualização disponível") if available else tr("Atualizado"), "dim")
            state.setStyleSheet(f"color: {ACCENT if available else DIM};")
            row.addWidget(state)
        return frame

    def _update_self(self) -> None:
        if not self.printer.can_act:
            self.note.setText(tr("Não é possível atualizar durante uma impressão."))
            return
        confirm(
            self,
            tr("Atualizar o MBindScreen? O ecrã reinicia no fim."),
            lambda: self.api.call(
                "machine.update.upgrade", {"name": OWN_UPDATE_NAME}, self._refreshed
            ),
            tr("Atualizar"),
        )


class ScreenPage(SubPage):
    def __init__(self, printer, api, back) -> None:
        super().__init__(tr("Ecrã"), back)
        self.printer, self.api = printer, api
        text = label(
            tr("O KlipperScreen continua instalado. Podes mudar a qualquer momento, mesmo "
            "durante uma impressão: a impressão não é afetada. A máquina arranca com o "
            "último ecrã escolhido.")
        )
        text.setWordWrap(True)
        self.body.addWidget(text)
        self.body.addWidget(
            button(tr("Mudar para o KlipperScreen"), self._switch, "accent", 64)
        )
        self.note = label("", "dim")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)
        self.body.addStretch()

    def _switch(self) -> None:
        confirm(
            self,
            tr("Mudar para o KlipperScreen? O ecrã fica preto alguns segundos."),
            lambda: screenSwitch.switch_to_klipperscreen(self.api, self._failed),
            tr("Mudar"),
        )

    def _failed(self, message: str) -> None:
        self.note.setText(tr("Não foi possível mudar: {}", message))


class RestartPage(SubPage):
    def __init__(self, printer, api, back) -> None:
        super().__init__(tr("Reiniciar"), back)
        self.printer, self.api = printer, api
        self.buttons = []
        items = (
            (tr("Reiniciar o Klipper"), "printer.restart", False),
            (tr("Reiniciar o firmware"), "printer.firmware_restart", False),
            (tr("Reiniciar o computador"), "machine.reboot", True),
            (tr("Desligar o computador"), "machine.shutdown", True),
        )
        for text, method, danger in items:
            widget = button(
                text,
                lambda t=text, m=method, d=danger: self._ask(t, m, d),
                "danger" if danger else "",
                60,
            )
            self.body.addWidget(widget)
            self.buttons.append(widget)
        self.body.addStretch()
        printer.updated.connect(self.refresh)
        self.refresh()

    def _ask(self, text: str, method: str, danger: bool) -> None:
        confirm(self, f"{text}?", lambda: self.api.call(method), tr("Confirmar"), danger)

    def refresh(self) -> None:
        for widget in self.buttons:
            widget.setEnabled(not self.printer.is_printing)


def restart_screen() -> None:
    """The same process starts again, under the same service, in the new language."""
    logger.info("Restarting the screen")
    os.execv(sys.executable, [sys.executable, *sys.argv])


class SettingsTab(QtWidgets.QStackedWidget):
    def __init__(self, printer, api) -> None:
        super().__init__()
        self.main = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(self.main)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        root.addWidget(label(tr("Definições"), "pageTitle"))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        root.addLayout(grid)
        self.addWidget(self.main)
        self.messages = MessagesPage(printer, self.reset)
        back_to_network = lambda: self.setCurrentWidget(self.network)  # noqa: E731
        self.wifi = WifiPage(api, back_to_network)
        self.hotspot = HotspotPage(api, back_to_network)
        self.network = NetworkPage(
            api,
            lambda: self.setCurrentWidget(self.wifi),
            lambda: self.setCurrentWidget(self.hotspot),
            self.reset,
        )
        self.addWidget(self.wifi)
        self.addWidget(self.hotspot)
        pages = (
            ("bell", tr("Mensagens"), tr("Avisos e consola do Klipper."), self.messages),
            ("wifi", tr("Rede"), tr("Ethernet, Wi-Fi e hotspot."), self.network),
            ("info", tr("Sistema"), tr("Versões e endereço de rede."), SystemPage(api, self.reset)),
            ("update", tr("Atualizações"), tr("Estado do que o Moonraker atualiza."),
             UpdatesPage(printer, api, self.reset)),
            ("screen", tr("Ecrã"), tr("Mudar para o KlipperScreen."),
             ScreenPage(printer, api, self.reset)),
            ("power", tr("Reiniciar"), tr("Klipper, firmware e computador."),
             RestartPage(printer, api, self.reset)),
        )
        for index, (icon_name, title, description, page) in enumerate(pages):
            self.addWidget(page)
            row = ListRow(icon_name, title, description)
            row.clicked.connect(lambda p=page: self.setCurrentWidget(p))
            grid.addWidget(row, index // MENU_COLUMNS, index % MENU_COLUMNS)
        self.language = ListRow("language", tr("Idioma"), i18n.LANGUAGES[i18n.language()])
        self.language.clicked.connect(self._choose_language)
        grid.addWidget(self.language, len(pages) // MENU_COLUMNS, len(pages) % MENU_COLUMNS)
        root.addStretch()

    def _choose_language(self) -> None:
        options = [(name, code) for code, name in i18n.LANGUAGES.items()]
        choose(self, tr("Idioma"), options, self._set_language)

    def _set_language(self, code: str) -> None:
        if code != i18n.language():
            i18n.save_language(code)
            restart_screen()

    def reset(self) -> None:
        self.setCurrentWidget(self.main)

    def open_messages(self) -> None:
        self.setCurrentWidget(self.messages)
