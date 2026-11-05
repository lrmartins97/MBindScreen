"""Small reusable widgets. Anything that knows about the printer lives in panels/."""
from __future__ import annotations

import typing

from lib.utils.icons import icon, pixmap
from lib.utils.theme import ACCENT, DIM, SLIDER_OFF, TEXT, TRACK
from PyQt6 import QtCore, QtGui, QtWidgets

CENTER = QtCore.Qt.AlignmentFlag.AlignCenter
Slot = typing.Callable[[], None]


class Clickable(QtWidgets.QFrame):
    """A frame that behaves like a button."""

    clicked = QtCore.pyqtSignal(name="clicked")

    def __init__(self, object_name: str = "card") -> None:
        super().__init__()
        self.setObjectName(object_name)

    def mouseReleaseEvent(self, event) -> None:
        if self.isEnabled() and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def label(text: str = "", name: str = "") -> QtWidgets.QLabel:
    widget = QtWidgets.QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


def button(
    text: str, callback: Slot, name: str = "", height: int = 0
) -> QtWidgets.QPushButton:
    widget = QtWidgets.QPushButton(text)
    if name:
        widget.setObjectName(name)
    if height:
        widget.setMinimumHeight(height)
    widget.clicked.connect(lambda _=False: callback())
    return widget


def card(margins: int = 14, spacing: int = 8) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("card")
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    return frame, layout


def set_active(widget: QtWidgets.QWidget, on: bool) -> None:
    """Toggle the [active="true"] style of a button."""
    if widget.property("active") != on:
        widget.setProperty("active", on)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def set_card_active(frame: QtWidgets.QFrame, on: bool) -> None:
    name = "cardActive" if on else "card"
    if frame.objectName() != name:
        frame.setObjectName(name)
        frame.style().unpolish(frame)
        frame.style().polish(frame)


def scroll_column(spacing: int = 8) -> tuple[QtWidgets.QScrollArea, QtWidgets.QVBoxLayout]:
    """A column scrolled by dragging with a finger."""
    layout = QtWidgets.QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(0, 0, 0, 0)
    inner = QtWidgets.QWidget()
    inner.setLayout(layout)
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(inner)
    QtWidgets.QScroller.grabGesture(
        area.viewport(), QtWidgets.QScroller.ScrollerGestureType.LeftMouseButtonGesture
    )
    return area, layout


def clear_layout(layout: QtWidgets.QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class PopupBox(QtWidgets.QFrame):
    """Fixed-width box whose height follows its content, wrapped text included."""

    def __init__(self, width: int) -> None:
        super().__init__()
        self.setObjectName("popup")
        self.setFixedWidth(width)

    def fit(self) -> None:
        """Call after changing the content. Wrapped text makes the height depend on
        the width, which the outer centring layout would otherwise ignore."""
        layout = self.layout()
        layout.invalidate()
        if layout.hasHeightForWidth():
            self.setFixedHeight(layout.totalHeightForWidth(self.width()))
        else:  # without wrapped text totalHeightForWidth gives 1
            self.setFixedHeight(layout.totalSizeHint().height())

    def mousePressEvent(self, event) -> None:
        event.accept()  # a touch on the box is not a touch outside it

    def mouseReleaseEvent(self, event) -> None:
        event.accept()


def status_chip(text: str) -> QtWidgets.QLabel:
    chip = label(text, "chip")
    chip.setFixedHeight(22)
    policy = QtWidgets.QSizePolicy(
        QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
    )
    policy.setRetainSizeWhenHidden(True)  # both tool cards keep the same layout
    chip.setSizePolicy(policy)
    return chip


class ChoiceRow(QtWidgets.QWidget):
    """A row of mutually exclusive buttons (distances, speeds)."""

    def __init__(
        self, values: typing.Sequence[float], unit: str = "", index: int = 0
    ) -> None:
        super().__init__()
        self.values = list(values)
        self.index = index
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.buttons = []
        for i, value in enumerate(self.values):
            text = f"{value:g}{unit}"
            widget = button(text, lambda n=i: self.select(n), "choice", 44)
            layout.addWidget(widget)
            self.buttons.append(widget)
        self.select(index)

    @property
    def value(self) -> float:
        return self.values[self.index]

    def select(self, index: int) -> None:
        self.index = index
        for i, widget in enumerate(self.buttons):
            set_active(widget, i == index)


class SubPage(QtWidgets.QWidget):
    """Back arrow and title; content goes into ``self.body``."""

    def __init__(self, title: str, back: Slot) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 14)
        layout.setSpacing(8)
        self.head = QtWidgets.QHBoxLayout()
        back_button = button("‹", back, "back")
        back_button.setFixedSize(46, 46)
        self.head.addWidget(back_button)
        self.head.addWidget(label(title, "pageTitle"))
        self.head.addStretch()
        layout.addLayout(self.head)
        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(8)
        layout.addLayout(self.body, 1)


class ListRow(Clickable):
    """Icon, title and description; tap to act."""

    def __init__(self, icon_name: str, title: str, description: str = "") -> None:
        super().__init__("card")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)
        picture = QtWidgets.QLabel()
        picture.setPixmap(pixmap(icon_name, ACCENT, 32))
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(1)
        self.title = label(title, "value")
        self.description = label(description, "dim")
        self.description.setWordWrap(True)
        column.addWidget(self.title)
        if description:
            column.addWidget(self.description)
        layout.addWidget(picture)
        layout.addLayout(column, 1)
        layout.addWidget(label("›", "heroSub"))


class LevelSlider(QtWidgets.QWidget):
    """Touch slider 0-100. Sends ``released`` once, when the finger lifts."""

    released = QtCore.pyqtSignal(int, name="released")
    MARGIN = 16

    def __init__(self) -> None:
        super().__init__()
        self.value, self.dragging = 0, False
        self.setFixedHeight(40)
        self.setMinimumWidth(120)

    def set_value(self, value: float) -> None:
        if not self.dragging:
            self.value = max(0, min(100, int(round(value))))
            self.update()

    def _from_x(self, x: float) -> None:
        span = max(self.width() - 2 * self.MARGIN, 1)
        self.value = round(100 * min(max((x - self.MARGIN) / span, 0.0), 1.0))
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.isEnabled():
            self.dragging = True
            self._from_x(event.position().x())

    def mouseMoveEvent(self, event) -> None:
        if self.dragging:
            self._from_x(event.position().x())

    def mouseReleaseEvent(self, event) -> None:
        if self.dragging:
            self.dragging = False
            self._from_x(event.position().x())
            self.released.emit(self.value)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        span = self.width() - 2 * self.MARGIN
        y = self.height() / 2
        x = self.MARGIN + span * self.value / 100
        color = QtGui.QColor(ACCENT if self.isEnabled() else SLIDER_OFF)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(TRACK))
        painter.drawRoundedRect(QtCore.QRectF(self.MARGIN, y - 5, span, 10), 5, 5)
        painter.setBrush(color)
        painter.drawRoundedRect(QtCore.QRectF(self.MARGIN, y - 5, x - self.MARGIN, 10), 5, 5)
        painter.setPen(QtGui.QPen(color, 4))
        painter.setBrush(QtGui.QColor("#ffffff"))
        painter.drawEllipse(QtCore.QPointF(x, y), 13, 13)


class Ring(QtWidgets.QWidget):
    """Circular progress with a value and a caption inside."""

    def __init__(self) -> None:
        super().__init__()
        self.value, self.text, self.caption, self.color = 0.0, "0%", "", ACCENT
        self.setMinimumSize(170, 170)

    def set(self, value: float, text: str, caption: str, color: str) -> None:
        self.value, self.text, self.caption, self.color = value, text, caption, color
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 24
        rect = QtCore.QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        pen = QtGui.QPen(QtGui.QColor(TRACK), 14)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        if self.value > 0:
            pen.setColor(QtGui.QColor(self.color))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -int(self.value * 360 * 16))
        font = painter.font()
        font.setPixelSize(int(side * 0.22))
        painter.setFont(font)
        painter.setPen(QtGui.QColor(TEXT))
        painter.drawText(
            QtCore.QRectF(rect.x(), rect.y() + side * 0.28, side, side * 0.3), CENTER, self.text
        )
        font.setPixelSize(13)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(DIM))
        painter.drawText(
            QtCore.QRectF(rect.x(), rect.y() + side * 0.58, side, 24), CENTER, self.caption
        )


class NavBar(QtWidgets.QFrame):
    """Left bar: one button per tab, emergency stop at the bottom."""

    selected = QtCore.pyqtSignal(int, name="selected")
    emergency = QtCore.pyqtSignal(name="emergency")

    def __init__(self, names: typing.Sequence[str]) -> None:
        super().__init__()
        self.setObjectName("nav")
        self.setFixedWidth(84)
        self.names = list(names)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 8)
        layout.setSpacing(2)
        self.group = QtWidgets.QButtonGroup(self)
        self.buttons = []
        for i in range(len(self.names)):
            widget = QtWidgets.QToolButton()
            widget.setCheckable(True)
            widget.setFixedSize(84, 62)
            widget.setIconSize(QtCore.QSize(34, 34))
            self.group.addButton(widget, i)
            layout.addWidget(widget)
            self.buttons.append(widget)
        self.group.idClicked.connect(self.selected)
        layout.addStretch()
        stop = QtWidgets.QToolButton()
        stop.setObjectName("estop")
        stop.setFixedSize(68, 62)
        stop.setIcon(icon("stop", "#ffffff", 34))
        stop.setIconSize(QtCore.QSize(34, 34))
        stop.clicked.connect(lambda _=False: self.emergency.emit())
        layout.addWidget(stop, alignment=CENTER)
        self.badge = QtWidgets.QLabel(self.buttons[-1])
        self.badge.setObjectName("badge")
        self.badge.setFixedSize(18, 18)
        self.badge.setAlignment(CENTER)
        self.badge.move(52, 10)
        self.badge.hide()
        self.set_current(0)

    def set_current(self, index: int) -> None:
        for i, widget in enumerate(self.buttons):
            widget.setChecked(i == index)
            widget.setIcon(icon(self.names[i], ACCENT if i == index else DIM, 34))

    def set_alerts(self, count: int) -> None:
        self.badge.setVisible(count > 0)
        self.badge.setText(str(min(count, 9)))
