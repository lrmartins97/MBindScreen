"""MoonWebSocket against a local websocket server speaking Moonraker's JSON-RPC."""
import json

import pytest
from lib.moonrakerComm import MoonWebSocket
from lib.printer import Printer
from PyQt6 import QtCore, QtNetwork, QtWebSockets


class FakeMoonraker(QtCore.QObject):
    """Answers the start-up sequence and records every request."""

    def __init__(self) -> None:
        super().__init__()
        self.requests = []
        self.klippy_state = "ready"
        self.error_for = {}
        self.client = None
        self.server = QtWebSockets.QWebSocketServer(
            "fake", QtWebSockets.QWebSocketServer.SslMode.NonSecureMode
        )
        assert self.server.listen(QtNetwork.QHostAddress.SpecialAddress.LocalHost, 0)
        self.port = self.server.serverPort()
        self.server.newConnection.connect(self._accept)

    def _accept(self) -> None:
        self.client = self.server.nextPendingConnection()
        self.client.textMessageReceived.connect(self._on_text)

    def notify(self, method, *params) -> None:
        self.client.sendTextMessage(
            json.dumps({"jsonrpc": "2.0", "method": method, "params": list(params)})
        )

    def _on_text(self, text: str) -> None:
        request = json.loads(text)
        self.requests.append(request)
        method = request["method"]
        reply = {"jsonrpc": "2.0", "id": request["id"]}
        if method in self.error_for:
            reply["error"] = {"code": 400, "message": self.error_for[method]}
        else:
            reply["result"] = self._result(method)
        self.client.sendTextMessage(json.dumps(reply))

    def _result(self, method: str):
        if method == "printer.info":
            return {"state": self.klippy_state, "state_message": "A arrancar"}
        if method == "printer.objects.list":
            return {"objects": ["toolhead", "extruder", "extruder1", "gcode_macro _MATERIAL_1"]}
        if method == "printer.objects.query":
            return {"status": {"configfile": {"settings": {"extruder": {"max_temp": 90}}}}}
        if method == "printer.objects.subscribe":
            return {"status": {"extruder": {"temperature": 30.0, "target": 37.0}}}
        return "ok"

    def methods(self):
        return [r["method"] for r in self.requests]


@pytest.fixture
def server(qapp):
    fake = FakeMoonraker()
    yield fake
    fake.server.close()


@pytest.fixture
def linked(qtbot, server):
    client = MoonWebSocket("127.0.0.1", server.port)
    printer = Printer()
    printer.connect_to(client)
    client.open()
    return client, printer


def test_start_up_sequence_reaches_ready_with_data(qtbot, server, linked):
    _client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    order = server.methods()
    assert order.index("printer.info") < order.index("printer.objects.list")
    assert order.index("printer.objects.query") < order.index("printer.objects.subscribe")
    assert printer.tool(0).target == 37.0
    assert printer.max_temp(0) == 90
    subscribed = next(
        r for r in server.requests if r["method"] == "printer.objects.subscribe"
    )["params"]["objects"]
    assert subscribed["gcode_macro _MATERIAL_1"] == ["name"]
    assert "manual_probe" not in subscribed  # this fake Klipper does not have it


def test_read_only_sends_nothing_that_acts_on_the_machine(qtbot, server):
    client = MoonWebSocket("127.0.0.1", server.port, read_only=True)
    printer = Printer()
    printer.connect_to(client)
    client.open()
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)  # reading still works
    results = []
    client.gcode("G28", lambda r, e: results.append(e))
    for method in ("printer.print.start", "printer.restart", "printer.firmware_restart",
                   "machine.reboot", "machine.shutdown", "machine.update.upgrade"):
        client.call(method, {}, lambda r, e: results.append(e))
    assert len(results) == 7 and all("experiência" in e["message"] for e in results)
    assert printer.alerts  # visible on the screen
    client.call("printer.emergency_stop")
    client.call("machine.services.start", {"service": "KlipperScreen"})
    qtbot.waitUntil(lambda: "machine.services.start" in server.methods(), timeout=2000)
    sent = server.methods()
    assert "printer.emergency_stop" in sent
    assert not {"printer.gcode.script", "printer.print.start", "printer.restart",
                "printer.firmware_restart", "machine.reboot", "machine.shutdown",
                "machine.update.upgrade"} & set(sent)


def test_klipper_not_ready_is_reported_then_retried(qtbot, server):
    server.klippy_state = "startup"
    client = MoonWebSocket("127.0.0.1", server.port)
    printer = Printer()
    printer.connect_to(client)
    client.open()
    qtbot.waitUntil(lambda: printer.klippy == "startup", timeout=3000)
    assert not printer.ready
    server.klippy_state = "ready"
    qtbot.waitUntil(lambda: printer.ready, timeout=4000)


def test_gcode_status_and_console_notifications(qtbot, server, linked):
    client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    results = []
    client.gcode("SERINGA_T0 MM=1 SPEED=0.5", lambda r, e: results.append((r, e)))
    qtbot.waitUntil(lambda: bool(results), timeout=2000)
    assert results == [("ok", None)]
    assert server.requests[-1]["params"] == {"script": "SERINGA_T0 MM=1 SPEED=0.5"}
    server.notify("notify_status_update", {"extruder": {"temperature": 36.5}}, 1.0)
    qtbot.waitUntil(lambda: printer.tool(0).temperature == 36.5, timeout=2000)
    assert printer.tool(0).target == 37.0  # partial update keeps the other fields
    server.notify("notify_gcode_response", "!! Falhou")
    qtbot.waitUntil(lambda: len(printer.alerts) == 1, timeout=2000)


def test_error_from_moonraker_reaches_the_callback(qtbot, server, linked):
    client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    server.error_for["machine.services.start"] = "Service 'KlipperScreen' not allowed"
    results = []
    client.call(
        "machine.services.start", {"service": "KlipperScreen"}, lambda r, e: results.append(e)
    )
    qtbot.waitUntil(lambda: bool(results), timeout=2000)
    assert "not allowed" in results[0]["message"]


def test_shutdown_and_ready_notifications(qtbot, server, linked):
    _client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    server.notify("notify_klippy_shutdown")
    qtbot.waitUntil(lambda: printer.klippy == "shutdown", timeout=2000)
    server.notify("notify_klippy_ready")
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)


def test_own_update_finished_is_signalled(qtbot, server, linked):
    client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    with qtbot.waitSignal(client.self_updated, timeout=2000):
        server.notify(
            "notify_update_response", {"application": "mbind-ui", "complete": True}
        )


def test_link_loss_answers_pending_calls_and_reconnects(qtbot, server, linked):
    client, printer = linked
    qtbot.waitUntil(lambda: printer.ready, timeout=3000)
    server.client.textMessageReceived.disconnect()  # the answer will never come
    results = []
    client.gcode("CALIBRATE_IDEX", lambda r, e: results.append(e))
    qtbot.wait(50)
    server.client.close()
    qtbot.waitUntil(lambda: not printer.link, timeout=2000)
    assert results and "perdida" in results[0]["message"]
    qtbot.waitUntil(lambda: printer.ready, timeout=5000)
