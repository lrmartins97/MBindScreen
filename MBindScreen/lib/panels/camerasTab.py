"""The machine's cameras: all of them in a grid, and one at full size.

The list comes from Moonraker, as set up in Mainsail. The grid refreshes slowly
because the Pi also runs the print; only the camera opened at full size is fluid.
"""
from __future__ import annotations

import logging

from lib import machine
from lib.panels.widgets.cameraView import CameraView, camera_transform
from lib.utils.widgets import SubPage, label
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)
GRID_INTERVAL_MS = 1000
GRID_PAGE = 0
GRID_COLUMNS = 2
MAX_CAMERAS_IN_TWO_COLUMNS = 4


class CamerasTab(QtWidgets.QWidget):
    def __init__(self, api) -> None:
        super().__init__()
        self.api = api
        self.cameras: list[machine.Camera] = []
        self.tiles: list[CameraView] = []
        self.big_views: list[CameraView] = []
        self.pages = QtWidgets.QStackedLayout(self)
        grid_page = QtWidgets.QWidget()
        column = QtWidgets.QVBoxLayout(grid_page)
        column.setContentsMargins(12, 12, 12, 12)
        self.message = label("A procurar câmaras...", "dim")
        self.message.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        column.addWidget(self.message)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(8)
        column.addLayout(self.grid, 1)
        self.pages.addWidget(grid_page)

    def reset(self) -> None:
        self.pages.setCurrentIndex(GRID_PAGE)

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
        self.reset()
        while self.pages.count() > GRID_PAGE + 1:
            page = self.pages.widget(GRID_PAGE + 1)
            self.pages.removeWidget(page)
            page.setParent(None)
        for tile in self.tiles:
            tile.hide()
            self.grid.removeWidget(tile)
            tile.setParent(None)  # a frame on its way may still arrive: not deleted
        self.tiles, self.big_views = [], []

    def _build(self, cameras: list[machine.Camera]) -> None:
        self._clear()
        self.cameras = cameras
        self.message.setText("Sem câmaras configuradas")
        self.message.setVisible(not cameras)
        columns = GRID_COLUMNS if len(cameras) <= MAX_CAMERAS_IN_TWO_COLUMNS else GRID_COLUMNS + 1
        for index, camera in enumerate(cameras):
            url = self.api.camera_url(camera.path)
            transform = camera_transform(
                camera.flip_horizontal, camera.flip_vertical, camera.rotation
            )
            tile = CameraView(
                self.api, url, False, GRID_INTERVAL_MS, transform, camera.name
            )
            tile.clicked.connect(lambda i=index: self.pages.setCurrentIndex(GRID_PAGE + 1 + i))
            self.grid.addWidget(tile, index // columns, index % columns)
            self.tiles.append(tile)
            page = SubPage(camera.name, self.reset)
            big = CameraView(self.api, url, False, transform=transform)
            page.body.addWidget(big, 1)
            self.pages.addWidget(page)
            self.big_views.append(big)
