"""Interactive steps Klipper leaves open: paper test (manual_probe) and bed screws.

Driven only by Klipper state, so it also appears if the step was started from
Mainsail, and closes by itself when the step ends anywhere.
"""
from __future__ import annotations

from lib import gcodeCommands as gc
from lib.utils.widgets import CENTER, Clickable, PopupBox, button, label
from PyQt6 import QtCore, QtWidgets

Z_STEPS = (-1.0, -0.1, -0.05, -0.01, 0.01, 0.05, 0.1, 1.0)


class AdjustOverlay(Clickable):
    def __init__(self, printer, api, window: QtWidgets.QWidget) -> None:
        super().__init__("scrim")
        self.setParent(window)
        self.printer, self.api = printer, api
        self.box = PopupBox(640)
        layout = QtWidgets.QVBoxLayout(self.box)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        self.title = label("", "cardTitle")
        self.hint = label("", "dim")
        self.hint.setWordWrap(True)
        self.value = label("", "big")
        self.value.setAlignment(CENTER)
        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        layout.addWidget(self.value)

        self.steps = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.steps)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        for index, step in enumerate(Z_STEPS):
            text = f"{step:+g}"
            grid.addWidget(
                button(text, lambda s=step: self.api.gcode(gc.test_z(s)), height=56),
                index // 4,
                index % 4,
            )
        layout.addWidget(self.steps)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(10)
        self.abort = button("Cancelar", lambda: self.api.gcode(gc.ABORT), height=54)
        self.adjusted = button(
            "Ajustei o parafuso", lambda: self.api.gcode(gc.ADJUSTED), height=54
        )
        self.accept = button("Aceitar", lambda: self.api.gcode(gc.ACCEPT), "accent", 54)
        for widget in (self.abort, self.adjusted, self.accept):
            row.addWidget(widget)
        layout.addLayout(row)
        outer = QtWidgets.QVBoxLayout(self)
        outer.addStretch()
        outer.addWidget(self.box, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        outer.addStretch()
        printer.updated.connect(self.refresh)
        self.hide()

    def refresh(self) -> None:
        probe = self.printer.get("manual_probe", "is_active", False)
        screws = self.printer.get("bed_screws", "is_active", False)
        self.setVisible(bool(probe or screws))
        if not self.isVisible():
            return
        self.raise_()
        self.steps.setVisible(bool(probe))
        self.adjusted.setVisible(not probe)
        if probe:
            z = self.printer.get("manual_probe", "z_position", None)
            self.title.setText("Teste do papel")
            self.hint.setText(
                "Sobe o prato até o bico prender ligeiramente uma folha de papel. "
                "Valores negativos aproximam o prato do bico."
            )
            self.value.setText("—" if z is None else f"Z {z:.3f} mm")
        else:
            screw = self.printer.get("bed_screws", "current_screw", 0) or 0
            accepted = self.printer.get("bed_screws", "accepted_screws", 0) or 0
            stage = self.printer.get("bed_screws", "state", "")
            self.title.setText("Ajuste dos parafusos do prato")
            self.hint.setText(
                "Roda o parafuso até o bico prender a folha de papel. Se mexeste nele, "
                "carrega em Ajustei o parafuso; se já estava bem, em Aceitar."
            )
            self.value.setText(
                f"Parafuso {screw + 1}"
                + (" · ajuste fino" if stage == "fine" else "")
                + f" · {accepted} aceites"
            )
        self.box.fit()
