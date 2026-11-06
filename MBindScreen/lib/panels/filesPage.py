"""File browser for the gcodes folder (the USB stick appears as the USB folder)."""
from __future__ import annotations

from lib.i18n import tr
import logging
import posixpath

from lib import machine
from lib.panels.widgets.dialogs import confirm
from lib.utils.icons import pixmap
from lib.utils.theme import ACCENT, DIM
from lib.utils.widgets import (
    Clickable,
    SubPage,
    button,
    clear_layout,
    label,
    scroll_column,
)
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
THUMB = 52
MAX_THUMBS = 30


class FileRow(Clickable):
    def __init__(self, icon_name: str, title: str, detail: str) -> None:
        super().__init__("card")
        self.setFixedHeight(66)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(12)
        self.picture = label()
        self.picture.setFixedSize(THUMB, THUMB)
        self.picture.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.picture.setPixmap(pixmap(icon_name, ACCENT if icon_name == "files" else DIM, 36))
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(0)
        name = label(title, "value")
        name.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )
        column.addWidget(name)
        if detail:
            column.addWidget(label(detail, "dim"))
        layout.addWidget(self.picture)
        layout.addLayout(column, 1)

    def set_thumbnail(self, image) -> None:
        if image is not None:
            self.picture.setPixmap(
                image.scaled(
                    THUMB,
                    THUMB,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )


class FilesPage(SubPage):
    def __init__(self, printer, api, back) -> None:
        super().__init__(tr("Ficheiros"), back)
        self.printer, self.api = printer, api
        self.path = ""
        self.up = button(tr("Pasta acima"), self._go_up, height=46)
        self.head.addWidget(self.up)
        self.head.addWidget(button(tr("Atualizar"), self.load, height=46))
        self.area, self.column = scroll_column(6)
        self.body.addWidget(self.area, 1)

    def showEvent(self, event) -> None:
        self.load()
        super().showEvent(event)

    def _go_up(self) -> None:
        self.path = posixpath.dirname(self.path)
        self.load()

    def load(self) -> None:
        self.up.setVisible(bool(self.path))
        root = posixpath.join("gcodes", self.path) if self.path else "gcodes"
        self.api.call(
            "server.files.get_directory", {"path": root, "extended": True}, self._loaded
        )

    def _loaded(self, result, error) -> None:
        clear_layout(self.column)
        if error or not result:
            self.column.addWidget(label(tr("Não foi possível ler os ficheiros."), "heroSub"))
            return
        folders = [
            d for d in result.get("dirs", []) if not d.get("dirname", "").startswith(".")
        ]
        for folder in sorted(folders, key=lambda d: d["dirname"].lower()):
            row = FileRow("files", folder["dirname"], "")
            row.clicked.connect(lambda name=folder["dirname"]: self._enter(name))
            self.column.addWidget(row)
        files = [
            f for f in result.get("files", []) if f.get("filename", "").endswith(".gcode")
        ]
        files.sort(key=lambda f: f.get("modified", 0), reverse=True)
        for index, item in enumerate(files):
            self._add_file(item, index < MAX_THUMBS)
        if not folders and not files:
            self.column.addWidget(label(tr("Pasta vazia."), "heroSub"))
        self.column.addStretch()

    def _add_file(self, item: dict, with_thumbnail: bool) -> None:
        name = item["filename"]
        estimate = item.get("estimated_time")
        detail = tr("Estimativa {}", machine.format_time(estimate)) if estimate else ""
        row = FileRow("file", name, detail)
        row.clicked.connect(lambda: self._ask_print(name, estimate))
        self.column.addWidget(row)
        thumbnails = item.get("thumbnails") or []
        if with_thumbnail and thumbnails:
            biggest = max(thumbnails, key=lambda t: t.get("size", 0))
            relative = posixpath.join(self.path, biggest.get("relative_path", ""))
            self.api.fetch_image(relative, row.set_thumbnail)

    def _enter(self, name: str) -> None:
        self.path = posixpath.join(self.path, name)
        self.load()

    def _ask_print(self, name: str, estimate) -> None:
        if not self.printer.can_act:
            return
        detail = tr("\nEstimativa: {}", machine.format_time(estimate)) if estimate else ""
        full = posixpath.join(self.path, name)
        confirm(
            self,
            tr("Imprimir {}?{}", name, detail),
            lambda: self._start(full),
            tr("Imprimir"),
        )

    def _start(self, full: str) -> None:
        logger.info("Print start: %s", full)
        self.api.call("printer.print.start", {"filename": full}, self._started)

    def _started(self, _result, error) -> None:
        if error:
            text = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            self.printer.add_alert(tr("Não foi possível iniciar: {}", text))
