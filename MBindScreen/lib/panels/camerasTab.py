"""The machine's cameras: a menu to see all of them or each one at full size.

The list comes from Moonraker, as set up in Mainsail. The grid refreshes slowly
because the Pi also runs the print; only a camera shown alone is fluid. The kTAMV
view is the nozzle camera again, so it has a menu button but no place in the grid.
"""
from __future__ import annotations

import logging

from lib import machine
from lib.panels.widgets.cameraView import FRAME_INTERVAL_MS, CameraView, camera_transform
from lib.utils.widgets import button, label, set_active
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
GRID_INTERVAL_MS = 1000
ANALYSIS_INTERVAL_MS = 500  # do not compete with the vision server during a calibration
ALL_CAMERAS = 0  # first page and first menu button; camera n is at n + 1
GRID_COLUMNS = 2
MAX_CAMERAS_IN_TWO_COLUMNS = 4


class CamerasTab(QtWidgets.QWidget):
    def __init__(self, api) -> None:
        super().__init__()
        self.api = api
        self.cameras: list[machine.Camera] = []
        self.choices: list[QtWidgets.QPushButton] = []
        self.tiles: list[CameraView] = []
        self.big_views: list[CameraView] = []
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(8)
        self.menu = QtWidgets.QHBoxLayout()
        self.menu.setSpacing(6)
        root.addLayout(self.menu)
        self.pages = QtWidgets.QStackedWidget()
        root.addWidget(self.pages, 1)
        grid_page = QtWidgets.QWidget()
        column = QtWidgets.QVBoxLayout(grid_page)
        column.setContentsMargins(0, 0, 0, 0)
        self.message = label("A procurar câmaras...", "dim")
        self.message.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        column.addWidget(self.message)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(8)
        column.addLayout(self.grid, 1)
        self.pages.addWidget(grid_page)

    def reset(self) -> None:
        self.choose(ALL_CAMERAS)

    def choose(self, page: int) -> None:
        self.pages.setCurrentIndex(page)
        for index, choice in enumerate(self.choices):
            set_active(choice, index == page)

    def showEvent(self, event) -> None:
        self.api.call("server.webcams.list", {}, self._on_list)
        super().showEvent(event)

    def _on_list(self, result, error) -> None:
        if error:
            logger.warning("No camera list: %s", error)
            self.message.setText("Não foi possível obter a lista de câmaras")
            self.message.show()
            return
        cameras = machine.cameras_from_webcams(result.get("webcams", []))
        if cameras != self.cameras or not cameras:
            self._build(cameras)

    def _clear(self) -> None:
        self.choose(ALL_CAMERAS)
        while self.pages.count() > ALL_CAMERAS + 1:
            page = self.pages.widget(ALL_CAMERAS + 1)
            self.pages.removeWidget(page)
            page.setParent(None)
        for widget in self.tiles + self.choices:
            widget.hide()
            widget.setParent(None)  # a frame on its way may still arrive: not deleted
        self.tiles, self.big_views, self.choices = [], [], []

    def _add_choice(self, text: str, page: int) -> None:
        choice = button(text, lambda: self.choose(page), "choice", 44)
        self.menu.addWidget(choice)
        self.choices.append(choice)

    def _build(self, cameras: list[machine.Camera]) -> None:
        self._clear()
        self.cameras = cameras
        self.message.setText("Sem câmaras configuradas")
        self.message.setVisible(not cameras)
        if cameras:
            self._add_choice("Todas", ALL_CAMERAS)
        in_grid = [camera for camera in cameras if not camera.is_analysis]
        columns = GRID_COLUMNS if len(in_grid) <= MAX_CAMERAS_IN_TWO_COLUMNS else GRID_COLUMNS + 1
        for index, camera in enumerate(cameras):
            page = index + 1
            url = self.api.camera_url(camera.path)
            transform = camera_transform(
                camera.flip_horizontal, camera.flip_vertical, camera.rotation
            )
            self._add_choice(camera.name, page)
            if not camera.is_analysis:
                tile = CameraView(self.api, url, False, GRID_INTERVAL_MS, transform, camera.name)
                tile.clicked.connect(lambda p=page: self.choose(p))
                position = len(self.tiles)
                self.grid.addWidget(tile, position // columns, position % columns)
                self.tiles.append(tile)
            interval = ANALYSIS_INTERVAL_MS if camera.is_analysis else FRAME_INTERVAL_MS
            big = CameraView(self.api, url, False, interval, transform)
            self.pages.addWidget(big)
            self.big_views.append(big)
        self.choose(ALL_CAMERAS)
