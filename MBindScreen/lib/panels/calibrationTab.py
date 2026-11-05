"""Calibration: the commands of calibracao/comandos.cfg and altura_e_prato.cfg."""
from __future__ import annotations

from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import choose, confirm, numpad
from lib.utils.widgets import ListRow, button, card, label, scroll_column
from PyQt6 import QtWidgets

TRIM_LIMIT = 0.5  # mm per adjustment of the T1 height


class CalibrationTab(QtWidgets.QWidget):
    def __init__(self, printer, api, runner) -> None:
        super().__init__()
        self.printer, self.api, self.runner = printer, api, runner
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        root.addWidget(label("Calibração", "pageTitle"))

        self.save_card, save_layout = card(12, 6)
        self.save_text = label("", "dim")
        self.save_text.setWordWrap(True)
        self.save_button = button("Gravar e reiniciar", self._save, "accent", 48)
        save_layout.addWidget(self.save_text)
        save_layout.addWidget(self.save_button)
        root.addWidget(self.save_card)

        area, column = scroll_column(6)
        self.rows = []
        items = (
            ("calibrate", "Calibração entre ferramentas",
             "Z e X/Y do T1 em relação ao T0 (CALIBRATE_IDEX).", self._full),
            ("calibrate", "Só X/Y entre bicos", "Exige o Z calibrado.", self._xy),
            ("calibrate", "Só Z entre bicos", "Depois é preciso refazer o X/Y.", self._z),
            ("info", "Estado da calibração", "Offsets, estado e datas.", self._status),
            ("move", "Altura do Z do T0", "Teste do papel (CALIBRAR_Z).", self._z_t0),
            ("move", "Nivelar o prato", "Ajuste dos 3 parafusos.", self._bed),
            ("move", "Ajuste fino do T1", "Soma à altura calibrada do T1.", self._trim),
            ("move", "Altura de uma placa", "Fundo de uma placa ou caixa de Petri.", self._plate),
            ("calibrate", "Foco da câmara", "Depois de mexer na lente.", self._focus),
        )
        for icon_name, title, description, action in items:
            row = ListRow(icon_name, title, description)
            row.clicked.connect(action)
            column.addWidget(row)
            self.rows.append(row)
        column.addStretch()
        root.addWidget(area, 1)
        printer.updated.connect(self.refresh)
        self.refresh()

    # --- actions --------------------------------------------------------
    def _run(self, title: str, script: str) -> None:
        if self.printer.can_act:
            self.runner.start(title, script)

    def _method(self, title: str, automatic: str, manual: str) -> None:
        choose(
            self,
            title,
            (("Automático", automatic), ("Manual", manual)),
            lambda script: self._run(title, script),
        )

    def _full(self) -> None:
        options = (
            ("Automática (câmara e switch)", gc.calibrate_idex()),
            ("Z pelo papel", gc.calibrate_idex(z_manual=True)),
            ("X/Y pela mira", gc.calibrate_idex(xy_manual=True)),
        )
        choose(
            self,
            "Calibração entre ferramentas",
            options,
            lambda script: self._run("Calibração entre ferramentas", script),
        )

    def _xy(self) -> None:
        self._method("Calibração X/Y", gc.calibrate_xy(), gc.calibrate_xy(manual=True))

    def _z(self) -> None:
        self._method("Calibração Z", gc.calibrate_z(), gc.calibrate_z(manual=True))

    def _status(self) -> None:
        self._run("Estado da calibração", gc.CALIBRATION_STATUS)

    def _z_t0(self) -> None:
        self._run("Altura do Z do T0", gc.CALIBRATE_Z_T0)

    def _bed(self) -> None:
        self._run("Nivelar o prato", gc.ADJUST_BED)

    def _plate(self) -> None:
        self._run("Altura de uma placa", gc.MEASURE_PLATE)

    def _focus(self) -> None:
        self._run("Foco da câmara", gc.CALIBRATE_FOCUS)

    def _trim(self) -> None:
        def ask(direction: float) -> None:
            numpad(
                self,
                "Ajuste do T1 (mm)",
                0.01,
                TRIM_LIMIT,
                lambda value: self._run(
                    "Ajuste fino do T1", gc.trim_t1(direction * value)
                ),
                decimals=True,
            )

        choose(
            self,
            "Ajuste fino do T1",
            (("Afastar do prato (+)", 1.0), ("Aproximar do prato (−)", -1.0)),
            ask,
        )

    def _save(self) -> None:
        confirm(
            self,
            "Gravar os valores novos? O Klipper reinicia.",
            lambda: self.api.gcode(gc.SAVE_CONFIG),
            "Gravar",
        )

    # --- display --------------------------------------------------------
    def refresh(self) -> None:
        printer = self.printer
        idle = printer.can_act
        for row in self.rows:
            row.setEnabled(idle)
        pending = printer.pending_save
        self.save_card.setVisible(bool(pending))
        unsafe = machine.unsafe_pending_save(pending)
        if unsafe:
            self.save_text.setText(
                "Não gravar: há valores do input shaper pendentes, e com estes o "
                "Klipper não arranca nesta máquina. Reinicia o Klipper para os descartar."
            )
        else:
            self.save_text.setText(f"Valores por gravar: {', '.join(pending)}")
        self.save_button.setVisible(not unsafe)
        self.save_button.setEnabled(idle)
