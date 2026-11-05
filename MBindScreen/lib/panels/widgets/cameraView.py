"""Live camera image with an optional aiming mark.

Asks for one snapshot at a time, so a slow network never piles up requests, and
only while the widget is on screen. The digital zoom crops around the centre, so
the mark stays on the same camera pixel at every zoom level.
"""
from __future__ import annotations

import logging
import typing

from PyQt6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)
FRAME_INTERVAL_MS = 100
MARK_COLOR = "#ff2d55"
NO_IMAGE_BG = "#1d3a4f"
RING_RADII = (0.08, 0.18)  # of the shorter side of the image
MISSED_FRAMES_FOR_WARNING = 3


class CameraView(QtWidgets.QWidget):
    def __init__(self, api, url: str, show_mark: bool = True) -> None:
        super().__init__()
        self.api, self.url, self.show_mark = api, url, show_mark
        self.zoom = 1
        self.frame: typing.Optional[QtGui.QPixmap] = None
        self.missed = 0
        self._running = False
        self._waiting = False
        self.setMinimumSize(320, 240)

    # --- polling --------------------------------------------------------
    def showEvent(self, event) -> None:
        self._running = True
        self._request()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._running = False
        super().hideEvent(event)

    def _request(self) -> None:
        if self._running and not self._waiting:
            self._waiting = True
            self.api.fetch_camera(self.url, self._on_frame)

    def _on_frame(self, frame: typing.Optional[QtGui.QPixmap]) -> None:
        self._waiting = False
        if frame is None:
            self.missed += 1
            if self.missed == MISSED_FRAMES_FOR_WARNING:
                logger.warning("No image from %s", self.url)
        else:
            self.frame, self.missed = frame, 0
        self.update()
        if self._running:
            QtCore.QTimer.singleShot(FRAME_INTERVAL_MS, self._request)

    def set_zoom(self, zoom: int) -> None:
        self.zoom = zoom
        self.update()

    # --- drawing --------------------------------------------------------
    @property
    def has_image(self) -> bool:
        return self.frame is not None and self.missed < MISSED_FRAMES_FOR_WARNING

    def _visible_part(self) -> QtGui.QPixmap:
        frame = self.frame
        width, height = frame.width() // self.zoom, frame.height() // self.zoom
        return frame.copy(
            (frame.width() - width) // 2, (frame.height() - height) // 2, width, height
        )

    def _draw_mark(self, painter: QtGui.QPainter, area: QtCore.QRect) -> None:
        painter.setPen(QtGui.QPen(QtGui.QColor(MARK_COLOR), 1))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        center = QtCore.QPointF(area.center())
        painter.drawLine(
            QtCore.QPointF(area.left(), center.y()), QtCore.QPointF(area.right(), center.y())
        )
        painter.drawLine(
            QtCore.QPointF(center.x(), area.top()), QtCore.QPointF(center.x(), area.bottom())
        )
        side = min(area.width(), area.height())
        for ratio in RING_RADII:
            painter.drawEllipse(center, side * ratio, side * ratio)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QtGui.QColor(NO_IMAGE_BG))
        if not self.has_image:
            painter.setPen(QtGui.QColor("#ffffff"))
            painter.drawText(
                self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "Sem imagem da câmara"
            )
            return
        image = self._visible_part().scaled(
            self.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        area = QtCore.QRect(QtCore.QPoint(0, 0), image.size())
        area.moveCenter(self.rect().center())
        painter.drawPixmap(area, image)
        if self.show_mark:
            self._draw_mark(painter, area)

