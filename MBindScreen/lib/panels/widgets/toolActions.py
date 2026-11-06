"""Choosing a head and its temperature: the same from every page."""
from __future__ import annotations

from lib.i18n import tr
from lib import gcodeCommands as gc
from lib.panels.widgets.dialogs import numpad


def select_tool(printer, api, tool: int) -> None:
    if printer.can_act and tool != printer.active_tool:
        api.gcode(gc.select_tool(tool, printer.homed()))


def edit_temperature(anchor, printer, api, tool: int) -> None:
    """Holding a head also selects it: that is the one being worked on."""
    if not printer.ready:
        return
    select_tool(printer, api, tool)
    numpad(
        anchor,
        tr("Temperatura T{}", tool),
        printer.tool(tool).target,
        printer.max_temp(tool),
        lambda value: api.gcode(gc.set_temperature(tool, value)),
    )
