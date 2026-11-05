"""Swap between MBindScreen and KlipperScreen.

The two systemd units conflict, so starting one stops the other: Moonraker does
the start and this process needs no sudo. The file below is what the
mbind-screen-boot service reads to pick the screen at the next boot.
"""
from __future__ import annotations

import logging
import pathlib
import subprocess
import typing

logger = logging.getLogger(__name__)
BOOT_FILE = pathlib.Path.home() / ".config" / "mbind-screen" / "boot-screen"
MBIND, KLIPPERSCREEN = "mbind", "klipperscreen"
SERVICES = {MBIND: "MBindScreen", KLIPPERSCREEN: "KlipperScreen"}


def write_boot_screen(screen: str, path: pathlib.Path = BOOT_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(screen + "\n", encoding="utf-8")


def read_boot_screen(path: pathlib.Path = BOOT_FILE) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return KLIPPERSCREEN
    return value if value in SERVICES else KLIPPERSCREEN


def start_directly() -> bool:
    """Fallback: Moonraker only knows the units that were loaded when it started."""
    try:
        result = subprocess.run(
            ["systemctl", "--no-block", "start", f"{SERVICES[KLIPPERSCREEN]}.service"],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def switch_to_klipperscreen(
    api, on_error: typing.Callable[[str], None], path: pathlib.Path = BOOT_FILE
) -> None:
    """Record the choice, then ask Moonraker to start KlipperScreen (this app is stopped)."""
    previous = read_boot_screen(path)
    write_boot_screen(KLIPPERSCREEN, path)

    def done(_result, error) -> None:
        if not error:
            return
        message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        logger.warning("Moonraker did not start KlipperScreen: %s", message)
        if not start_directly():
            write_boot_screen(previous, path)
            on_error(message)

    logger.info("Switching to KlipperScreen")
    api.call("machine.services.start", {"service": SERVICES[KLIPPERSCREEN]}, done)
