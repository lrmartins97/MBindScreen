"""Live camera image with an optional aiming mark.

Asks for one snapshot at a time, so a slow network never piles up requests, and
only while the widget is on screen. The digital zoom crops around the centre, so
the mark stays on the same camera pixel at every zoom level.
"""
from __future__ import annotations

from lib.i18n import tr
import logging
import typing

from PyQt6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)
FRAME_INTERVAL_MS = 100
MARK_COLOR = "#ff2d55"
NO_IMAGE_BG = "#1d3a4f"
CORNER_RADIUS = 12
RING_RADII = (0.08, 0.18)  # of the shorter side of the image
MISSED_FRAMES_FOR_WARNING = 3
CAPTION_MARGIN = 8
CAPTION_PADDING = (10, 4)
CAPTION_BG = QtGui.QColor(0, 0, 0, 150)


def camera_transform(
    flip_horizontal: bool, flip_vertical: bool, rotation: int
) -> QtGui.QTransform:
    """Mainsail's flips and rotation. Without them some images are upside down."""
    transform = QtGui.QTransform()
    transform.rotate(rotation)
    transform.scale(-1 if flip_horizontal else 1, -1 if flip_vertical else 1)
    return transform


class CameraView(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(name="clicked")

    def __init__(
        self,
        api,
        url: str,
        show_mark: bool = True,
        interval_ms: int = FRAME_INTERVAL_MS,
        transform: typing.Optional[QtGui.QTransform] = None,
        caption: str = "",
        rounded: bool = False,
    ) -> None:
        super().__init__()
        self.api, self.url, self.show_mark = api, url, show_mark
        self.interval_ms = interval_ms
        self.transform = transform or QtGui.QTransform()
        self.caption = caption
        self.rounded = rounded
        self.zoom = 1
        self.frame: typing.Optional[QtGui.QPixmap] = None
        self.missed = 0
        self._running = False
        self._waiting = False
        self.setMinimumSize(160, 120)

    def mouseReleaseEvent(self, event) -> None:
        if self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

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
            self.frame, self.missed = frame.transformed(self.transform), 0
        self.update()
        if self._running:
            QtCore.QTimer.singleShot(self.interval_ms, self._request)

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

    def _draw_caption(self, painter: QtGui.QPainter) -> None:
        box = painter.fontMetrics().boundingRect(self.caption)
        box.adjust(-CAPTION_PADDING[0], -CAPTION_PADDING[1], *CAPTION_PADDING)
        box.moveTopLeft(QtCore.QPoint(CAPTION_MARGIN, CAPTION_MARGIN))
        painter.fillRect(box, CAPTION_BG)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.drawText(box, QtCore.Qt.AlignmentFlag.AlignCenter, self.caption)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        if self.rounded:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            outline = QtGui.QPainterPath()
            outline.addRoundedRect(QtCore.QRectF(self.rect()), CORNER_RADIUS, CORNER_RADIUS)
            painter.setClipPath(outline)
        painter.fillRect(self.rect(), QtGui.QColor(NO_IMAGE_BG))
        if not self.has_image:
            painter.setPen(QtGui.QColor("#ffffff"))
            painter.drawText(
                self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, tr("Sem imagem da câmara")
            )
            if self.caption:
                self._draw_caption(painter)
            return
        fit = (
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
            if self.rounded
            else QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )
        image = self._visible_part().scaled(
            self.size(), fit, QtCore.Qt.TransformationMode.SmoothTransformation
        )
        area = QtCore.QRect(QtCore.QPoint(0, 0), image.size())
        area.moveCenter(self.rect().center())
        painter.drawPixmap(area, image)
        if self.show_mark:
            self._draw_mark(painter, area)
        if self.caption:
            self._draw_caption(painter)

