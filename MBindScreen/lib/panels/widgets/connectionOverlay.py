"""Full-window page while Moonraker or Klipper are not ready."""
from __future__ import annotations

import logging

from lib import machine, screenSwitch
from lib.panels.widgets.dialogs import confirm
from lib.utils.widgets import CENTER, button, label
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)


class ConnectionOverlay(QtWidgets.QFrame):
    def __init__(self, printer, api, window: QtWidgets.QWidget) -> None:
        super().__init__(window)
        self.printer, self.api = printer, api
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(14)
        self.title = label("", "heroTitle")
        self.title.setAlignment(CENTER)
        self.text = label("", "heroSub")
        self.text.setAlignment(CENTER)
        self.text.setWordWrap(True)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        self.firmware = button("Reiniciar firmware", self._firmware, "accent", 60)
        self.klipper = button("Reiniciar Klipper", self._restart, height=60)
        row.addWidget(self.firmware)
        row.addWidget(self.klipper)
        layout.addLayout(row)
        self.other = button(
            "Mudar para o KlipperScreen", self._switch, height=52
        )
        layout.addWidget(self.other)
        layout.addStretch()
        printer.updated.connect(self.refresh)
        self.refresh()

    def _firmware(self) -> None:
        self.api.call("printer.firmware_restart")

    def _restart(self) -> None:
        self.api.call("printer.restart")

    def _switch(self) -> None:
        confirm(
            self,
            "Mudar para o KlipperScreen?",
            lambda: screenSwitch.switch_to_klipperscreen(self.api, self.printer.add_alert),
            "Mudar",
        )

    def refresh(self) -> None:
        printer = self.printer
        self.setVisible(not printer.ready)
        if printer.ready:
            return
        self.raise_()
        if not printer.link:
            self.title.setText("A ligar ao Moonraker…")
            self.text.setText("A aguardar pelo serviço da impressora.")
        else:
            self.title.setText(machine.KLIPPY_TITLES.get(printer.klippy, printer.klippy))
            self.text.setText(printer.klippy_message or "")
        for widget in (self.firmware, self.klipper, self.other):
            widget.setVisible(printer.link and printer.klippy != "startup")
