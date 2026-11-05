"""Line icons on a 24x24 grid, drawn as SVG and rendered in any colour."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtSvg

GEAR = (
    '<path d="M19.3 10.0 L22.1 10.5 L22.1 13.5 L19.3 14.0 L18.6 15.8 L20.2 18.1 '
    "L18.1 20.2 L15.8 18.6 L14.0 19.3 L13.5 22.1 L10.5 22.1 L10.0 19.3 L8.2 18.6 "
    "L5.9 20.2 L3.8 18.1 L5.4 15.8 L4.7 14.0 L1.9 13.5 L1.9 10.5 L4.7 10.0 L5.4 8.2 "
    'L3.8 5.9 L5.9 3.8 L8.2 5.4 L10.0 4.7 L10.5 1.9 L13.5 1.9 L14.0 4.7 L15.8 5.4 '
    'L18.1 3.8 L20.2 5.9 L18.6 8.2 Z"/><circle cx="12" cy="12" r="3.2"/>'
)
PATHS = {
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    "controls": '<path d="M5 4v16M12 4v16M19 4v16"/><path d="M3 9h4M10 15h4M17 8h4"/>',
    "syringe": (
        '<path d="M9 2h6M12 2v5"/><path d="M8 7h8v11H8z"/><path d="M8 11h3M8 14h3"/>'
        '<path d="M10.5 18h3l-1.5 4z"/>'
    ),
    "cameras": '<path d="M3 8h4l2-3h6l2 3h4v11H3z"/><circle cx="12" cy="13" r="3.5"/>',
    "arrow_left": '<path d="M20 12H4M10 6l-6 6 6 6"/>',
    "arrow_right": '<path d="M4 12h16M14 6l6 6-6 6"/>',
    "arrow_up": '<path d="M12 20V4M6 10l6-6 6 6"/>',
    "arrow_down": '<path d="M12 4v16M6 14l6 6 6-6"/>',
    "wifi": (
        '<path d="M2 9a15 15 0 0120 0M5.5 12.5a10 10 0 0113 0M9 16a5 5 0 016 0"/>'
        '<path d="M12 19.5h.01"/>'
    ),
    "ethernet": (
        '<rect x="3" y="3" width="18" height="12" rx="1"/><path d="M8 15v3h8v-3M12 18v3"/>'
    ),
    "hotspot": (
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M8 8a6 6 0 000 8M16 8a6 6 0 010 8M5 5a10 10 0 000 14M19 5a10 10 0 010 14"/>'
    ),
    "calibrate": (
        '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2"/>'
        '<path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>'
    ),
    "settings": GEAR,
    "files": (
        '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>'
    ),
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    "print": '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 21h16"/>',
    "stop": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "move": (
        '<path d="M12 3v18M3 12h18M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3"/>'
    ),
    "fan": (
        '<circle cx="12" cy="12" r="2"/><path d="M12 10c0-4 1-7 4-7 2 0 3 2 2 4-1 2-3 3-6 3z'
        "M14 12c4 0 7 1 7 4 0 2-2 3-4 2-2-1-3-3-3-6zM12 14c0 4-1 7-4 7-2 0-3-2-2-4 1-2 3-3 6-3z"
        'M10 12c-4 0-7-1-7-4 0-2 2-3 4-2 2 1 3 3 3 6z"/>'
    ),
    "bulb": (
        '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 00-4 10.5c.7.7 1 1.5 1 2.5h6'
        'c0-1 .3-1.8 1-2.5A6 6 0 0012 3z"/>'
    ),
    "uv": (
        '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3'
        'M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>'
    ),
    "brush": '<path d="M9 15l-4 5"/><path d="M9 15l7-7 3 3-7 7z"/><path d="M14 4l6 6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
    "update": (
        '<path d="M20 11a8 8 0 00-14-4L3 10M3 4v6h6"/>'
        '<path d="M4 13a8 8 0 0014 4l3-3M21 20v-6h-6"/>'
    ),
    "screen": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "bell": '<path d="M6 16v-5a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21a2 2 0 004 0"/>',
    "power": '<path d="M12 3v9"/><path d="M6.5 7a8 8 0 1011 0"/>',
    "folder_up": '<path d="M12 19V7M7 12l5-5 5 5"/>',
}
_cache: dict[tuple, QtGui.QPixmap] = {}


def pixmap(name: str, color: str, size: int = 32) -> QtGui.QPixmap:
    key = (name, color, size)
    if key not in _cache:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{PATHS[name]}</svg>'
        )
        image = QtGui.QPixmap(size, size)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(image)
        QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode())).render(painter)
        painter.end()
        _cache[key] = image
    return _cache[key]


def icon(name: str, color: str, size: int = 32) -> QtGui.QIcon:
    return QtGui.QIcon(pixmap(name, color, size))
