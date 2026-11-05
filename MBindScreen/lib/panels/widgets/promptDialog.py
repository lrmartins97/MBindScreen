"""Shows the Klipper host prompts (used by the manual X/Y calibration)."""
from __future__ import annotations

import logging

from lib.prompts import Prompt, PromptButton, is_align_prompt
from lib.utils.widgets import CENTER, Clickable, PopupBox, button, clear_layout, label
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)
STYLES = {"primary": "accent", "error": "danger"}


class PromptDialog(Clickable):
    def __init__(self, printer, api, window: QtWidgets.QWidget) -> None:
        super().__init__("scrim")
        self.setParent(window)
        self.api = api
        self.box = PopupBox(620)
        self.layout_ = QtWidgets.QVBoxLayout(self.box)
        self.layout_.setContentsMargins(20, 16, 20, 16)
        self.layout_.setSpacing(8)
        outer = QtWidgets.QVBoxLayout(self)
        outer.addStretch()
        outer.addWidget(self.box, alignment=CENTER)
        outer.addStretch()
        printer.prompt_show.connect(self.show_prompt)
        printer.prompt_close.connect(self.hide)
        self.hide()

    def _button(self, spec: PromptButton) -> QtWidgets.QPushButton:
        return button(
            spec.label, lambda: self.api.gcode(spec.gcode), STYLES.get(spec.style, ""), 46
        )

    def show_prompt(self, prompt: Prompt) -> None:
        logger.info("Prompt: %s", prompt.title)
        if is_align_prompt(prompt):
            return  # shown by AlignPage, with the camera
        clear_layout(self.layout_)
        self.layout_.addWidget(label(prompt.title, "cardTitle"))
        for line in prompt.lines:
            text = label(line)
            text.setWordWrap(True)
            self.layout_.addWidget(text)
        for group in prompt.rows:
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(6)
            for spec in group:
                row.addWidget(self._button(spec))
            self.layout_.addLayout(row)
        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(10)
        for spec in prompt.footer:
            footer.addWidget(self._button(spec))
        self.layout_.addLayout(footer)
        self.box.fit()
        self.show()
        self.raise_()
