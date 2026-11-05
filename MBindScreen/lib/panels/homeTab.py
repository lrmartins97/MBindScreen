"""Home: machine state at a glance, the two tools and the way to the files."""
from __future__ import annotations

import pathlib

from lib import machine
from lib.utils.icons import pixmap
from lib.utils.theme import ACCENT
from lib.utils.widgets import Clickable, label, set_card_active, status_chip
from PyQt6 import QtCore, QtGui, QtWidgets

PHOTO = pathlib.Path(__file__).resolve().parent.parent / "ui" / "resources" / "mbind.png"


class ToolCard(Clickable):
    def __init__(self, tool: int) -> None:
        super().__init__("card")
        self.tool_index = tool
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(2)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(label(f"T{tool}", "cardTitle"))
        self.chip = status_chip("Ativa")
        top.addStretch()
        top.addWidget(self.chip)
        self.temperature = label("—", "big")
        self.detail = label("", "dim")
        layout.addLayout(top)
        layout.addWidget(self.temperature)
        layout.addWidget(self.detail)

    def show_tool(self, tool) -> None:
        set_card_active(self, tool.active)
        self.chip.setVisible(tool.active)
        self.temperature.setText(f"{tool.temperature:.1f} °C")
        target = f"alvo {tool.target:.0f} °C" if tool.target else "desligada"
        self.detail.setText(f"{tool.material} · {target}")


class HomeTab(QtWidgets.QWidget):
    open_files = QtCore.pyqtSignal(name="open-files")
    open_syringes = QtCore.pyqtSignal(name="open-syringes")

    def __init__(self, printer) -> None:
        super().__init__()
        self.printer = printer
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        hero = QtWidgets.QHBoxLayout()
        hero.setSpacing(14)
        bar = QtWidgets.QFrame()
        bar.setObjectName("accentBar")
        bar.setFixedWidth(3)
        column = QtWidgets.QVBoxLayout()
        self.title = label("", "heroTitle")
        self.sub = label("", "heroSub")
        self.sub.setWordWrap(True)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        column.addStretch()
        for widget in (self.title, self.sub, self.progress):
            column.addWidget(widget)
        column.addStretch()
        hero.addWidget(bar)
        hero.addLayout(column, 3)
        photo = label()
        photo.setPixmap(
            QtGui.QPixmap(str(PHOTO)).scaledToHeight(
                300, QtCore.Qt.TransformationMode.SmoothTransformation
            )
        )
        photo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        hero.addWidget(photo, 2)
        root.addLayout(hero, 1)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        self.files = Clickable("card")
        self.files.setFixedHeight(130)
        self.files.clicked.connect(self.open_files.emit)
        files_layout = QtWidgets.QVBoxLayout(self.files)
        files_layout.setContentsMargins(18, 10, 18, 10)
        picture = label()
        picture.setPixmap(pixmap("files", ACCENT, 46))
        self.files_title = label("Ficheiros", "cardTitle")
        files_layout.addStretch()
        files_layout.addWidget(picture)
        files_layout.addWidget(self.files_title)
        files_layout.addStretch()
        row.addWidget(self.files, 4)
        self.tools = {tool: ToolCard(tool) for tool in machine.TOOLS}
        for card in self.tools.values():
            card.setFixedHeight(130)
            card.clicked.connect(self.open_syringes.emit)
            row.addWidget(card, 5)
        root.addLayout(row)
        printer.updated.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        printer = self.printer
        state = printer.print_state
        active = printer.is_printing
        progress = printer.get("virtual_sdcard", "progress", 0) or 0
        filename = (printer.get("print_stats", "filename", "") or "").rsplit("/", 1)[-1]
        self.title.setText(machine.PRINT_STATE_TITLES.get(state, state.title()))
        if active and filename:
            self.sub.setText(f"{filename} · {progress:.0%}")
        else:
            self.sub.setText("Sem home feito" if not printer.homed() else "Home feito")
        self.progress.setVisible(active)
        self.progress.setValue(int(progress * 1000))
        self.files_title.setText("Impressão" if active else "Ficheiros")
        for index, card in self.tools.items():
            card.show_tool(printer.tool(index))
