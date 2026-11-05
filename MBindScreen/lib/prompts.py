"""Klipper host prompts (``// action:prompt_*`` lines), as Mainsail and
KlipperScreen show them. The manual X/Y calibration is driven by these."""
from __future__ import annotations

import dataclasses
import typing

PREFIX = "action:prompt_"
ALIGN_NEXT = "CALIBRATE_IDEX_NEXT"


@dataclasses.dataclass(frozen=True)
class PromptButton:
    label: str
    gcode: str
    style: str = ""


@dataclasses.dataclass
class Prompt:
    title: str = ""
    lines: list[str] = dataclasses.field(default_factory=list)
    rows: list[list[PromptButton]] = dataclasses.field(default_factory=list)
    footer: list[PromptButton] = dataclasses.field(default_factory=list)


def parse_button(text: str) -> PromptButton:
    """``label|gcode|style``: gcode defaults to the label, style is optional."""
    parts = [part.strip() for part in text.split("|")]
    label = parts[0]
    gcode = parts[1] if len(parts) > 1 and parts[1] else label
    style = parts[2] if len(parts) > 2 else ""
    return PromptButton(label, gcode, style)


def is_align_prompt(prompt: Prompt) -> bool:
    """The manual X/Y prompt, which AlignPage shows instead of a dialog."""
    return any(item.gcode == ALIGN_NEXT for item in prompt.footer)


class PromptParser:
    """Feed it console lines; ``feed`` returns "show", "close" or None."""

    def __init__(self) -> None:
        self.prompt = Prompt()
        self._group: typing.Optional[list[PromptButton]] = None

    def feed(self, line: str) -> typing.Optional[str]:
        text = line.strip().removeprefix("//").strip()
        if not text.startswith(PREFIX):
            return None
        command, _, value = text[len(PREFIX):].partition(" ")
        value = value.strip()
        if command == "begin":
            self.prompt, self._group = Prompt(title=value), None
        elif command == "text":
            self.prompt.lines.append(value)
        elif command == "button":
            if self._group is not None:
                self._group.append(parse_button(value))
            else:
                self.prompt.rows.append([parse_button(value)])
        elif command == "button_group_start":
            self._group = []
        elif command == "button_group_end":
            if self._group:
                self.prompt.rows.append(self._group)
            self._group = None
        elif command == "footer_button":
            self.prompt.footer.append(parse_button(value))
        elif command == "show":
            return "show"
        elif command == "end":
            return "close"
        return None
