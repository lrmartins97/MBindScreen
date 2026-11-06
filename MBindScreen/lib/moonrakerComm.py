"""Moonraker JSON-RPC client over QWebSocket.

Runs on the Qt event loop (no threads), so a callback can touch widgets directly.
Reads go through Printer; panels only use ``gcode`` / ``call`` to act.
"""
from __future__ import annotations

from lib.i18n import tr
import json
import logging
import typing
from urllib.parse import quote

from lib import machine
from PyQt6 import QtCore, QtGui, QtNetwork, QtWebSockets

logger = logging.getLogger(__name__)
Callback = typing.Callable[[typing.Any, typing.Any], None]
ImageCallback = typing.Callable[[typing.Optional[QtGui.QPixmap]], None]
RETRY_MS = 2000
IMAGE_TIMEOUT_MS = 3000
APP_NAME = "MBindScreen"
UPDATE_NAME = "mbind-ui"  # section of moonraker.conf: Moonraker wants it in lower case

READ_ONLY_MESSAGE = tr("Modo de experiência: comando não enviado")
READ_ONLY_ALLOWED = (
    "printer.info",
    "printer.objects.",
    "printer.emergency_stop",
    "server.",
    "machine.system_info",
    "machine.update.status",
    "machine.services.start",  # the way back to KlipperScreen
)

SUBSCRIPTION: dict[str, typing.Optional[list[str]]] = {
    "webhooks": ["state", "state_message"],
    "print_stats": ["state", "filename", "message", "print_duration", "info"],
    "virtual_sdcard": ["progress", "is_active"],
    "display_status": ["message"],
    "extruder": ["temperature", "target", "power"],
    "extruder1": ["temperature", "target", "power"],
    "toolhead": ["homed_axes", "position", "extruder", "axis_minimum", "axis_maximum"],
    "dual_carriage": None,
    "gcode_move": ["homing_origin", "gcode_position", "speed_factor"],
    "manual_probe": ["is_active", "z_position", "z_position_lower", "z_position_upper"],
    "bed_screws": ["is_active", "state", "current_screw", "accepted_screws"],
    "configfile": ["save_config_pending", "save_config_pending_items"],
    "save_variables": ["variables"],
    "idle_timeout": ["state"],
    "pause_resume": ["is_paused"],
    machine.CHAMBER_FAN: ["speed"],
    machine.UV_PIN: ["value"],
    machine.CHAMBER_LIGHT: ["value"],
    machine.SERINGA_VARS: None,
    machine.ALIGN_VARS: ["active", "origin_set", "mode"],
}


def allowed_when_read_only(method: str) -> bool:
    """In a trial nothing may act on the machine, except stopping it or leaving."""
    return method.startswith(READ_ONLY_ALLOWED)


def build_subscription(names: typing.Iterable[str]) -> dict:
    """Subscribe only to what this Klipper has, plus any extra fan or sensor."""
    names = list(names)
    subs = {key: value for key, value in SUBSCRIPTION.items() if key in names}
    for name in names:
        if name.startswith(("fan_generic ", "temperature_sensor ")):
            subs.setdefault(name, None)
        elif name.startswith(machine.MATERIAL_PREFIX):
            subs[name] = ["name"]
    return subs


def is_own_update_done(response: dict) -> bool:
    """True when Moonraker reports that the update of this app has finished."""
    return bool(response.get("complete")) and response.get("application") == UPDATE_NAME


class MoonWebSocket(QtCore.QObject):
    link_up = QtCore.pyqtSignal(name="link-up")
    link_down = QtCore.pyqtSignal(name="link-down")
    status = QtCore.pyqtSignal(dict, name="status")
    klippy = QtCore.pyqtSignal(str, str, name="klippy")  # state, message
    gcode_response = QtCore.pyqtSignal(str, name="gcode-response")
    objects = QtCore.pyqtSignal(list, name="objects")
    settings = QtCore.pyqtSignal(dict, name="settings")
    self_updated = QtCore.pyqtSignal(name="self-updated")

    def __init__(self, host: str, port: int, parent=None, read_only: bool = False) -> None:
        super().__init__(parent)
        self.read_only = read_only
        self._ws_url = QtCore.QUrl(f"ws://{host}:{port}/websocket")
        self._host = host
        self._http = f"http://{host}:{port}"
        self._manager = QtNetwork.QNetworkAccessManager(self)
        self._ws = QtWebSockets.QWebSocket()
        self._ws.connected.connect(self._on_connected)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.textMessageReceived.connect(self._on_message)
        self._next_id = 1
        self._pending: dict[int, Callback] = {}
        self._up = False
        self._reconnect = QtCore.QTimer(self)
        self._reconnect.setInterval(RETRY_MS)
        self._reconnect.timeout.connect(self._try_open)
        self._klippy_retry = QtCore.QTimer(self)
        self._klippy_retry.setSingleShot(True)
        self._klippy_retry.setInterval(RETRY_MS)
        self._klippy_retry.timeout.connect(self._bootstrap)

    # --- connection -----------------------------------------------------
    def open(self) -> None:
        logger.info("Connecting to %s", self._ws_url.toString())
        self._try_open()
        self._reconnect.start()

    def _try_open(self) -> None:
        if self._ws.state() == QtNetwork.QAbstractSocket.SocketState.UnconnectedState:
            self._ws.open(self._ws_url)

    def _on_connected(self) -> None:
        logger.info("Websocket connected")
        self._up = True
        self._reconnect.stop()
        self.link_up.emit()
        self.call(
            "server.connection.identify",
            {
                "client_name": APP_NAME,
                "version": "0.1.0",
                "type": "display",
                "url": "https://github.com/lrmartins97/MBindScreen",
            },
        )
        self._bootstrap()

    def _on_disconnected(self) -> None:
        logger.warning("Websocket disconnected")
        self._up = False
        for callback in self._pending.values():
            callback(None, {"message": tr("Ligação ao Moonraker perdida")})
        self._pending.clear()
        self.link_down.emit()
        self._reconnect.start()

    # --- requests -------------------------------------------------------
    def call(
        self,
        method: str,
        params: typing.Optional[dict] = None,
        callback: typing.Optional[Callback] = None,
    ) -> None:
        if self.read_only and not allowed_when_read_only(method):
            logger.info("Read-only, not sent: %s %s", method, params)
            self.gcode_response.emit(f"!! {READ_ONLY_MESSAGE}")
            if callback:
                callback(None, {"message": READ_ONLY_MESSAGE})
            return
        if not self._up:
            logger.warning("Dropped %s: not connected", method)
            if callback:
                callback(None, {"message": tr("Sem ligação ao Moonraker")})
            return
        request: dict = {"jsonrpc": "2.0", "method": method, "id": self._next_id}
        if params:
            request["params"] = params
        if callback:
            self._pending[self._next_id] = callback
        self._next_id += 1
        logger.debug("-> %s %s", method, params)
        self._ws.sendTextMessage(json.dumps(request))

    def gcode(self, script: str, callback: typing.Optional[Callback] = None) -> None:
        logger.info("G-code: %s", script.replace("\n", " | "))
        self.call("printer.gcode.script", {"script": script}, callback)

    def fetch_image(self, path: str, callback: ImageCallback) -> None:
        """Download a thumbnail. ``path`` is relative to the gcodes folder."""
        self._get_pixmap(f"{self._http}/server/files/gcodes/{quote(path)}", callback)

    def fetch_camera(self, url: str, callback: ImageCallback) -> None:
        """Download a camera snapshot. ``url`` comes from camera_url."""
        self._get_pixmap(url, callback)

    def camera_url(self, path: str) -> str:
        """Camera paths go through nginx on port 80, like Mainsail and NozzleSight."""
        return path if "://" in path else f"http://{self._host}{path}"

    def _get_pixmap(self, url: str, callback: ImageCallback) -> None:
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        request.setTransferTimeout(IMAGE_TIMEOUT_MS)
        reply = self._manager.get(request)

        def done() -> None:
            pixmap = QtGui.QPixmap()
            ok = (
                reply.error() == QtNetwork.QNetworkReply.NetworkError.NoError
                and pixmap.loadFromData(reply.readAll())
            )
            reply.deleteLater()
            callback(pixmap if ok else None)

        reply.finished.connect(done)

    # --- start-up sequence: info -> objects -> settings -> subscribe ----
    def _bootstrap(self) -> None:
        self.call("printer.info", None, self._on_info)

    def _retry(self, state: str, message: str) -> None:
        self.klippy.emit(state, message)
        self._klippy_retry.start()

    def _on_info(self, result, error) -> None:
        if error or not result:
            self._retry("disconnected", "")
            return
        state, message = result.get("state", ""), result.get("state_message", "")
        if state != "ready":
            self._retry(state, message)
            return
        self.call("printer.objects.list", None, self._on_objects)

    def _on_objects(self, result, error) -> None:
        if error or not result:
            self._retry("startup", "")
            return
        names = result.get("objects", [])
        self.objects.emit(names)

        def subscribed(sub_result, sub_error) -> None:
            if sub_error or not sub_result:
                self._retry("startup", "")
                return
            self.klippy.emit("ready", "")
            self.status.emit(sub_result.get("status", {}))

        def got_settings(query_result, _error) -> None:
            status = (query_result or {}).get("status", {})
            self.settings.emit(status.get("configfile", {}).get("settings", {}))
            self.call(
                "printer.objects.subscribe",
                {"objects": build_subscription(names)},
                subscribed,
            )

        self.call(
            "printer.objects.query",
            {"objects": {"configfile": ["settings"]}},
            got_settings,
        )

    # --- incoming -------------------------------------------------------
    def _on_message(self, text: str) -> None:
        try:
            message = json.loads(text)
        except ValueError:
            logger.warning("Invalid JSON from Moonraker")
            return
        if "id" in message:
            callback = self._pending.pop(message["id"], None)
            if "error" in message:
                logger.warning("Moonraker error: %s", message["error"])
            if callback:
                callback(message.get("result"), message.get("error"))
            return
        method, params = message.get("method"), message.get("params") or []
        if method == "notify_status_update":
            self.status.emit(params[0])
        elif method == "notify_klippy_ready":
            self._bootstrap()
        elif method == "notify_klippy_shutdown":
            self.klippy.emit("shutdown", "")
        elif method == "notify_klippy_disconnected":
            self.klippy.emit("disconnected", "")
            self._klippy_retry.start()
        elif method == "notify_gcode_response":
            self.gcode_response.emit(params[0])
        elif method == "notify_update_response" and is_own_update_done(params[0]):
            logger.info("MBindScreen was updated")
            self.self_updated.emit()
