"""Calibration: the macros of calibracao/, grouped by what they are for."""
from __future__ import annotations

from lib.i18n import tr
from lib import gcodeCommands as gc
from lib import machine
from lib.panels.widgets.dialogs import choose, confirm, numpad
from lib.utils.widgets import ListRow, SubPage, button, card, label, scroll_column
from PyQt6 import QtWidgets

TRIM_LIMIT = 0.5  # mm per adjustment of the T1 height


class CalibrationTab(QtWidgets.QStackedWidget):
    """A first page of sections; each section opens the list of its macros."""

    def __init__(self, printer, api, runner) -> None:
        super().__init__()
        self.printer, self.api, self.runner = printer, api, runner
        self.main = QtWidgets.QWidget()
        self.addWidget(self.main)
        root = QtWidgets.QVBoxLayout(self.main)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        root.addWidget(label(tr("Calibração"), "pageTitle"))

        self.save_card, save_layout = card(12, 6)
        self.save_text = label("", "dim")
        self.save_text.setWordWrap(True)
        self.save_button = button(tr("Gravar e reiniciar"), self._save, "accent", 48)
        save_layout.addWidget(self.save_text)
        save_layout.addWidget(self.save_button)
        root.addWidget(self.save_card)

        self.rows = []
        sections = (
            ("calibrate", tr("Alinhar os bicos"), tr("Calibração entre o T0 e o T1, a mais importante."), (
                ("calibrate", tr("Calibração entre ferramentas"),
                 tr("Z e X/Y do T1 em relação ao T0 (CALIBRATE_IDEX)."), self._full),
                ("calibrate", tr("Só X/Y entre bicos"), tr("Exige o Z calibrado."), self._xy),
                ("calibrate", tr("Só Z entre bicos"), tr("Depois é preciso refazer o X/Y."), self._z),
                ("info", tr("Estado da calibração"), tr("Offsets, estado e datas."), self._status),
            )),
            ("move", tr("Altura e prato"), tr("Altura dos bicos, nivelamento e placas."), (
                ("move", tr("Altura do Z do T0"), tr("Teste do papel (CALIBRAR_Z)."), self._z_t0),
                ("move", tr("Nivelar o prato"), tr("Ajuste dos 3 parafusos."), self._bed),
                ("move", tr("Ajuste fino do T1"), tr("Soma à altura calibrada do T1."), self._trim),
                ("move", tr("Altura de uma placa"), tr("Fundo de uma placa ou caixa de Petri."),
                 self._plate),
            )),
            ("info", tr("Câmara e diagnóstico"), tr("Foco da câmara e medição de vibrações."), (
                ("calibrate", tr("Foco da câmara"), tr("Depois de mexer na lente."), self._focus),
                ("info", tr("Medir vibrações do T0"), tr("Só mede: não muda a configuração."),
                 lambda: self._resonance(0)),
                ("info", tr("Medir vibrações do T1"), tr("Só mede: não muda a configuração."),
                 lambda: self._resonance(1)),
            )),
        )
        for icon_name, title, description, items in sections:
            page = self._section_page(title, items)
            row = ListRow(icon_name, title, description)
            row.clicked.connect(lambda p=page: self.setCurrentWidget(p))
            root.addWidget(row)
        root.addStretch()
        printer.updated.connect(self.refresh)
        self.refresh()

    def _section_page(self, title: str, items: tuple) -> SubPage:
        page = SubPage(title, self.reset)
        area, column = scroll_column(6)
        for icon_name, row_title, description, action in items:
            row = ListRow(icon_name, row_title, description)
            row.clicked.connect(action)
            column.addWidget(row)
            self.rows.append(row)
        column.addStretch()
        page.body.addWidget(area, 1)
        self.addWidget(page)
        return page

    def reset(self) -> None:
        self.setCurrentWidget(self.main)

    # --- actions --------------------------------------------------------
    def _run(self, title: str, script: str) -> None:
        if self.printer.can_act:
            self.runner.start(title, script)

    def _method(self, title: str, automatic: str, manual: str) -> None:
        choose(
            self,
            title,
            ((tr("Automático"), automatic), ("Manual", manual)),
            lambda script: self._run(title, script),
        )

    def _full(self) -> None:
        options = (
            (tr("Automática (câmara e switch)"), gc.calibrate_idex()),
            (tr("Z pelo papel"), gc.calibrate_idex(z_manual=True)),
            (tr("X/Y pela mira"), gc.calibrate_idex(xy_manual=True)),
        )
        choose(
            self,
            tr("Calibração entre ferramentas"),
            options,
            lambda script: self._run(tr("Calibração entre ferramentas"), script),
        )

    def _xy(self) -> None:
        self._method(tr("Calibração X/Y"), gc.calibrate_xy(), gc.calibrate_xy(manual=True))

    def _z(self) -> None:
        self._method(tr("Calibração Z"), gc.calibrate_z(), gc.calibrate_z(manual=True))

    def _status(self) -> None:
        self._run(tr("Estado da calibração"), gc.CALIBRATION_STATUS)

    def _z_t0(self) -> None:
        self._run(tr("Altura do Z do T0"), gc.CALIBRATE_Z_T0)

    def _bed(self) -> None:
        self._run(tr("Nivelar o prato"), gc.ADJUST_BED)

    def _plate(self) -> None:
        self._run(tr("Altura de uma placa"), gc.MEASURE_PLATE)

    def _focus(self) -> None:
        self._run(tr("Foco da câmara"), gc.CALIBRATE_FOCUS)

    def _resonance(self, tool: int) -> None:
        self._run(tr("Medir vibrações do T{}", tool), gc.MEASURE_RESONANCE[tool])

    def _trim(self) -> None:
        def ask(direction: float) -> None:
            numpad(
                self,
                tr("Ajuste do T1 (mm)"),
                0.01,
                TRIM_LIMIT,
                lambda value: self._run(
                    tr("Ajuste fino do T1"), gc.trim_t1(direction * value)
                ),
                decimals=True,
            )

        choose(
            self,
            tr("Ajuste fino do T1"),
            ((tr("Afastar do prato (+)"), 1.0), (tr("Aproximar do prato (−)"), -1.0)),
            ask,
        )

    def _save(self) -> None:
        confirm(
            self,
            tr("Gravar os valores novos? O Klipper reinicia."),
            lambda: self.api.gcode(gc.SAVE_CONFIG),
            tr("Gravar"),
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
                tr("Não gravar: há valores do input shaper pendentes, e com estes o "
                "Klipper não arranca nesta máquina. Reinicia o Klipper para os descartar.")
            )
        else:
            self.save_text.setText(tr("Valores por gravar: {}", ', '.join(pending)))
        self.save_button.setVisible(not unsafe)
        self.save_button.setEnabled(idle)
