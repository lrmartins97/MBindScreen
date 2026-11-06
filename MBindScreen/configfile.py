"""MBindScreen.cfg reader. The copy in the printer config folder wins over the
one in the repository, so a machine can differ without dirtying the repo."""
from __future__ import annotations

import configparser
import dataclasses
import logging
import pathlib

logger = logging.getLogger(__name__)
REPO_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "MBindScreen.cfg"
MACHINE_CONFIG = pathlib.Path.home() / "printer_data" / "config" / "MBindScreen.cfg"
# Same camera and same snapshot as NozzleSight ([ktamv] in calibracao/camara.cfg).
DEFAULT_CALIBRATION_CAMERA = "/webcam2/snapshot?max_delay=0"
# SHA-256 of the developer mode code. Each machine can have its own in MBindScreen.cfg.
DEFAULT_DEVELOPER_CODE = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"


@dataclasses.dataclass(frozen=True)
class ScreenConfig:
    host: str = "localhost"
    port: int = 7125
    sleep_minutes: int = 0
    calibration_camera: str = DEFAULT_CALIBRATION_CAMERA
    calibration_mirror: bool = True  # as in Mainsail: the head and the image go the same way
    developer_code: str = DEFAULT_DEVELOPER_CODE


def load_config() -> ScreenConfig:
    parser = configparser.ConfigParser()
    read = parser.read([REPO_CONFIG, MACHINE_CONFIG], encoding="utf-8")
    logger.info("Config files read: %s", read)
    return ScreenConfig(
        host=parser.get("server", "host", fallback="localhost"),
        port=parser.getint("server", "port", fallback=7125),
        sleep_minutes=parser.getint("screen", "sleep_minutes", fallback=0),
        calibration_camera=parser.get(
            "camera", "calibration", fallback=DEFAULT_CALIBRATION_CAMERA
        ),
        calibration_mirror=parser.getboolean("camera", "calibration_mirror", fallback=True),
        developer_code=parser.get("screen", "developer_code", fallback=DEFAULT_DEVELOPER_CODE),
    )
