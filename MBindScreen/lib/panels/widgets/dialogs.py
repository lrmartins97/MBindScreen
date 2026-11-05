"""Modal boxes drawn over the whole window (the printer has no window manager)."""
from __future__ import annotations

import typing

from lib.utils.widgets import CENTER, Clickable, PopupBox, button, label
from PyQt6 import QtCore, QtWidgets


class Scrim(Clickable):
    """Dark layer over the window holding a centred box."""

    def __init__(self, anchor: QtWidgets.QWidget, width: int = 480) -> None:
        super().__init__("scrim")
        window = anchor.window()
        self.setParent(window)
        self.setGeometry(window.rect())
        self.box = PopupBox(width)
        self.content = QtWidgets.QVBoxLayout(self.box)
        self.content.setContentsMargins(22, 18, 22, 18)
        self.content.setSpacing(12)
        outer = QtWidgets.QVBoxLayout(self)
        outer.addStretch()
        outer.addWidget(self.box, alignment=CENTER)
        outer.addStretch()

    def open(self) -> None:
        self.box.fit()
        self.show()
        self.raise_()

    def close_box(self) -> None:
        self.hide()
        self.deleteLater()


def confirm(
    anchor: QtWidgets.QWidget,
    text: str,
    on_ok: typing.Callable[[], None],
    ok_text: str = "OK",
    danger: bool = False,
) -> Scrim:
    scrim = Scrim(anchor)
    message = label(text)
    message.setWordWrap(True)
    scrim.content.addWidget(message)
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(10)
    row.addWidget(button("Voltar", scrim.close_box, height=52))
    row.addWidget(
        button(
            ok_text,
            lambda: (scrim.close_box(), on_ok()),
            "danger" if danger else "accent",
            52,
        )
    )
    scrim.content.addLayout(row)
    scrim.open()
    return scrim


def choose(
    anchor: QtWidgets.QWidget,
    title: str,
    options: typing.Sequence[tuple[str, typing.Any]],
    on_pick: typing.Callable[[typing.Any], None],
) -> Scrim:
    """List of big buttons; picking one closes the box."""
    scrim = Scrim(anchor)
    scrim.content.addWidget(label(title, "cardTitle"))
    for text, value in options:
        scrim.content.addWidget(
            button(text, lambda v=value: (scrim.close_box(), on_pick(v)), height=50)
        )
    scrim.content.addWidget(button("Voltar", scrim.close_box, height=46))
    scrim.open()
    return scrim


def numpad(
    anchor: QtWidgets.QWidget,
    title: str,
    start: float,
    maximum: float,
    on_ok: typing.Callable[[float], None],
    minimum: float = 0.0,
    decimals: bool = False,
) -> Scrim:
    """Number entry. OK stays disabled while the value is out of range."""
    scrim = Scrim(anchor, 420)
    scrim.content.setSpacing(8)
    scrim.content.addWidget(label(f"{title} ({minimum:g} a {maximum:g})", "value"))
    display = label(f"{start:g}", "display")
    display.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    scrim.content.addWidget(display)
    state = {"text": f"{start:g}", "fresh": True}

    def parsed() -> typing.Optional[float]:
        try:
            value = float(state["text"])
        except ValueError:
            return None
        return value if minimum <= value <= maximum else None

    def show() -> None:
        display.setText(state["text"] or "0")
        ok.setEnabled(parsed() is not None)

    def press(key: str) -> None:
        if key == "⌫":
            state["text"] = state["text"][:-1]
        elif key == "." and "." in state["text"]:
            return
        else:
            state["text"] = key if state["fresh"] else state["text"] + key
        state["fresh"] = False
        show()

    grid = QtWidgets.QGridLayout()
    grid.setSpacing(6)
    keys = ["7", "8", "9", "4", "5", "6", "1", "2", "3", "." if decimals else "", "0", "⌫"]
    for index, key in enumerate(keys):
        if key:
            grid.addWidget(button(key, lambda k=key: press(k), height=48), index // 3, index % 3)
    scrim.content.addLayout(grid)
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(10)
    row.addWidget(button("Voltar", scrim.close_box, height=50))

    def accept() -> None:
        value = parsed()
        if value is not None:
            scrim.close_box()
            on_ok(value)

    ok = button("OK", accept, "accent", 50)
    row.addWidget(ok)
    scrim.content.addLayout(row)
    show()
    scrim.open()
    return scrim
