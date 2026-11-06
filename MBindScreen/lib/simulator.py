"""Fake M-BIND with the same interface as MoonWebSocket, for development without a
printer: python MBindScreen/MBindScreen.py --simulate

It understands the G-code in gcodeCommands.py. Real macro logic stays in Klipper:
a screen test here proves the screen, not the machine.
"""
from __future__ import annotations

import logging
import re

from lib import machine
from PyQt6 import QtCore, QtGui

logger = logging.getLogger(__name__)
TICK_MS = 200
CAMERA_CENTER = (30.0, 100.0)  # invented: real machines have their own
PIXELS_PER_MM = 40.0
CAMERA_START_OFFSET = {0: (0.6, -0.4), 1: (-0.9, 0.5)}
PRINT_SECONDS = 600.0
STAGE_SECONDS = 2.0
OBJECTS = [
    "webhooks", "configfile", "toolhead", "gcode_move", "print_stats",
    "virtual_sdcard", "display_status", "extruder", "extruder1", "dual_carriage",
    "manual_probe", "bed_screws", "save_variables", "idle_timeout", "pause_resume",
    machine.CHAMBER_FAN, machine.UV_PIN, machine.CHAMBER_LIGHT, machine.SERINGA_VARS,
    machine.ALIGN_VARS,
    f"{machine.MATERIAL_PREFIX}1", f"{machine.MATERIAL_PREFIX}2",
]
FILES = [
    {"filename": "comprimidos_x24.gcode", "modified": 3, "estimated_time": 2700},
    {"filename": "alginato_grelha.gcode", "modified": 2, "estimated_time": 900},
]


class SimulatedPrinter(QtCore.QObject):
    link_up = QtCore.pyqtSignal(name="link-up")
    link_down = QtCore.pyqtSignal(name="link-down")
    status = QtCore.pyqtSignal(dict, name="status")
    klippy = QtCore.pyqtSignal(str, str, name="klippy")
    gcode_response = QtCore.pyqtSignal(str, name="gcode-response")
    objects = QtCore.pyqtSignal(list, name="objects")
    settings = QtCore.pyqtSignal(dict, name="settings")
    self_updated = QtCore.pyqtSignal(name="self-updated")

    def __init__(self, parent=None, speed: float = 1.0) -> None:
        super().__init__(parent)
        self.speed = speed
        self.sent: list[str] = []  # every script received, for the tests
        self.calls: list[tuple] = []
        self.state = {
            "webhooks": {"state": "ready", "state_message": ""},
            "print_stats": {"state": "standby", "filename": "", "message": "",
                            "print_duration": 0.0, "info": {}},
            "virtual_sdcard": {"progress": 0.0, "is_active": False},
            "display_status": {"message": ""},
            "extruder": {"temperature": 24.0, "target": 0.0, "power": 0.0},
            "extruder1": {"temperature": 24.5, "target": 0.0, "power": 0.0},
            "toolhead": {"homed_axes": "", "position": [0, 0, 0, 0], "extruder": "extruder",
                         "axis_minimum": [-80, -5, -10, 0], "axis_maximum": [110, 120, 30, 0]},
            "dual_carriage": {"carriage_0": "PRIMARY", "carriage_1": "INACTIVE"},
            "gcode_move": {"homing_origin": [0, 0, 0, 0], "gcode_position": [0, 0, 0, 0],
                           "speed_factor": 1.0},
            "manual_probe": {"is_active": False, "z_position": None,
                             "z_position_lower": None, "z_position_upper": None},
            "bed_screws": {"is_active": False, "state": None, "current_screw": 0,
                           "accepted_screws": 0},
            "configfile": {"save_config_pending": False, "save_config_pending_items": {}},
            "save_variables": {"variables": {"tool_0_material": 1, "tool_1_material": 0}},
            machine.CHAMBER_FAN: {"speed": 0.0},
            machine.UV_PIN: {"value": 0.0},
            machine.CHAMBER_LIGHT: {"value": 1.0},
            machine.SERINGA_VARS: {"max_mm": 20.0, "max_speed": 3.0},
            machine.ALIGN_VARS: {"active": 0, "origin_set": 0, "mode": 0},
            f"{machine.MATERIAL_PREFIX}1": {"name": "Pasta Amido"},
            f"{machine.MATERIAL_PREFIX}2": {"name": "Pasta 2"},
        }
        self._print_clock = 0.0
        self.camera_ok = True
        self.camera_requests = 0
        self.webcams = [
            {"name": name, "enabled": True, "snapshot_url": f"/webcam{port}/?action=snapshot"}
            for name, port in (("Chamber", ""), ("Nozzle Cam", 2), ("tool 0", 3), ("tool 1", 4))
        ]
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    # --- same interface as MoonWebSocket --------------------------------
    def open(self) -> None:
        QtCore.QTimer.singleShot(0, self._connect)

    def _connect(self) -> None:
        self.link_up.emit()
        self.objects.emit(OBJECTS)
        self.settings.emit({
            "extruder": {"max_temp": 90.0, "filament_diameter": 15.0},
            "extruder1": {"max_temp": 90.0, "filament_diameter": 15.0},
        })
        self.klippy.emit("ready", "")
        self.status.emit(self.state)
        self._timer.start()

    def gcode(self, script: str, callback=None) -> None:
        logger.info("Simulated G-code: %s", script.replace("\n", " | "))
        self.sent.append(script)
        error = None
        for line in script.splitlines():
            error = self._run_line(line.strip())
            if error:
                self.gcode_response.emit(f"!! {error}")
                break
        self.status.emit(self.state)
        if callback:
            callback(None if error else "ok", {"message": error} if error else None)

    def call(self, method: str, params=None, callback=None) -> None:
        self.calls.append((method, params))
        if method == "printer.gcode.script":
            self.gcode(params["script"], callback)
            return
        if method == "server.webcams.list" and self.webcams is None:
            callback(None, {"message": "Moonraker sem resposta"})
            return
        result = self._rpc(method, params or {})
        self.status.emit(self.state)
        if callback:
            callback(result, None)

    def fetch_image(self, _path: str, callback) -> None:
        callback(None)

    def camera_url(self, path: str) -> str:
        return path

    def fetch_camera(self, _url: str, callback) -> None:
        """A nozzle seen from below: it moves with the head, in the 640x480 camera."""
        self.camera_requests += 1
        QtCore.QTimer.singleShot(
            0, lambda: callback(self._nozzle_image() if self.camera_ok else None)
        )

    def _nozzle_image(self) -> QtGui.QPixmap:
        image = QtGui.QPixmap(640, 480)
        image.fill(QtGui.QColor("#d8d8d8"))
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        x, y = self.state["toolhead"]["position"][:2]
        center = QtCore.QPointF(
            320 + (x - CAMERA_CENTER[0]) * PIXELS_PER_MM,
            240 - (y - CAMERA_CENTER[1]) * PIXELS_PER_MM,
        )
        painter.setBrush(QtGui.QColor("#555555"))
        painter.drawEllipse(center, 46, 46)
        painter.setBrush(QtGui.QColor("#111111"))
        painter.drawEllipse(center, 14, 14)
        painter.end()
        return image

    # --- JSON-RPC -------------------------------------------------------
    def _rpc(self, method: str, params: dict):
        if method == "server.webcams.list":
            return {"webcams": self.webcams}
        if method == "server.files.get_directory":
            return {"dirs": [{"dirname": "USB"}] if params["path"] == "gcodes" else [],
                    "files": FILES if params["path"] == "gcodes" else []}
        if method == "server.files.metadata":
            return {"estimated_time": 600, "layer_count": 40}
        if method == "printer.print.start":
            self._start_print(params["filename"])
        elif method == "printer.print.pause":
            self.state["print_stats"]["state"] = "paused"
        elif method == "printer.print.resume":
            self.state["print_stats"]["state"] = "printing"
        elif method == "printer.print.cancel":
            self.state["print_stats"]["state"] = "cancelled"
            self.state["display_status"]["message"] = ""
        elif method == "printer.emergency_stop":
            self.state["webhooks"].update(state="shutdown", state_message="Paragem de emergência")
            self.klippy.emit("shutdown", "Paragem de emergência")
        elif method in ("printer.firmware_restart", "printer.restart"):
            self.state["webhooks"].update(state="ready", state_message="")
            self.state["toolhead"]["homed_axes"] = ""
            self.klippy.emit("ready", "")
        elif method == "printer.info":
            return {"hostname": "MBind (simulada)", "software_version": "simulador"}
        elif method == "machine.system_info":
            return {"system_info": {"distribution": {"name": "Simulador"}, "network": {
                "wlan0": {"ip_addresses": [{"family": "ipv4", "address": "192.0.2.50"}]}}}}
        elif method == "machine.update.status":
            return {"version_info": {
                "MBindScreen": {"version": "v0.1.0", "remote_version": "v0.1.1",
                                "commits_behind": [{"sha": "abc"}]},
                "klipper": {"version": "v0.13", "commits_behind": []},
            }}
        return "ok"

    # --- G-code ---------------------------------------------------------
    @staticmethod
    def _params(line: str) -> dict:
        return {k.upper(): v for k, v in re.findall(r"(\w+)=(\S+)", line)}

    def _run_line(self, line: str):
        word = line.split(" ", 1)[0].upper() if line else ""
        params = self._params(line)
        toolhead = self.state["toolhead"]
        if word == "G28":
            toolhead["homed_axes"] = "xyz"
            toolhead["position"] = [0.0, 0.0, 8.0, 0.0]
            self.gcode_response.emit("// Home concluído")
        elif word == "G1":
            if self.state["print_stats"]["state"] in machine.ACTIVE_PRINT_STATES:
                return "Em impressão"
            for axis, value in re.findall(r"([XYZ])(-?[\d.]+)", line):
                toolhead["position"]["XYZ".index(axis)] += float(value)
        elif word in ("T0", "T1"):
            tool = int(word[1])
            self.state["dual_carriage"] = {
                "carriage_0": "PRIMARY" if tool == 0 else "INACTIVE",
                "carriage_1": "PRIMARY" if tool == 1 else "INACTIVE",
            }
            toolhead["extruder"] = machine.EXTRUDERS[tool]
        elif word == "SET_HEATER_TEMPERATURE":
            self.state[params["HEATER"]]["target"] = float(params["TARGET"])
        elif word.startswith("SERINGA_T"):
            if self.state["print_stats"]["state"] in machine.ACTIVE_PRINT_STATES:
                return f"{word}: nao disponivel durante uma impressao."
            self.gcode_response.emit(f"// {word[-2:]}: embolo {params.get('MM')} mm")
        elif word == "SET_MATERIAL":
            variables = self.state["save_variables"]["variables"]
            variables[f"tool_{params['TOOL']}_material"] = int(params["MATERIAL"])
        elif word == "SET_FAN_SPEED":
            self.state[f"fan_generic {params['FAN']}"]["speed"] = float(params["SPEED"])
        elif word == "SET_PIN":
            self.state[f"output_pin {params['PIN']}"]["value"] = float(params["VALUE"])
        elif word == "SET_GCODE_OFFSET":
            self.state["gcode_move"]["homing_origin"][2] += float(params["Z_ADJUST"])
        elif word in ("CALIBRAR_Z", "MEASURE_PLATE_HEIGHT"):
            toolhead["homed_axes"] = "xyz"
            self.state["manual_probe"].update(is_active=True, z_position=1.0)
        elif word == "TESTZ":
            self.state["manual_probe"]["z_position"] += float(params["Z"])
        elif word == "ACCEPT":
            if self.state["bed_screws"]["is_active"]:
                self._next_screw(accepted=True)
            else:
                self.state["manual_probe"].update(is_active=False, z_position=None)
                self.state["configfile"].update(
                    save_config_pending=True,
                    save_config_pending_items={"stepper_z": {"position_endstop": "0.1"}},
                )
        elif word == "ADJUSTED":
            self._next_screw(accepted=False)
        elif word == "ABORT":
            self.state["manual_probe"].update(is_active=False, z_position=None)
            self.state["bed_screws"].update(is_active=False)
        elif word == "AJUSTAR_CAMA":
            self.state["bed_screws"].update(
                is_active=True, state="adjust", current_screw=0, accepted_screws=0
            )
        elif word == "SAVE_CONFIG":
            self.state["configfile"].update(
                save_config_pending=False, save_config_pending_items={}
            )
            toolhead["homed_axes"] = ""
        elif (word == "CALIBRATE_IDEX_XY" and params.get("MANUAL") == "1") or (
            word == "CALIBRATE_IDEX" and params.get("XY_MANUAL") == "1"
        ):
            self.state[machine.ALIGN_VARS].update(active=1, origin_set=0)
            self._go_to_camera(0)
        elif word == "_ALIGN_JOG":
            position = toolhead["position"]
            position[0] += float(params.get("X", 0))
            position[1] += float(params.get("Y", 0))
        elif word == "CALIBRATE_IDEX_NEXT":
            self.gcode_response.emit("// action:prompt_end")
            if self.state[machine.ALIGN_VARS]["origin_set"] == 0:
                self.state[machine.ALIGN_VARS]["origin_set"] = 1
                self._go_to_camera(1)
            else:
                self.state[machine.ALIGN_VARS].update(active=0, origin_set=0)
                self.gcode_response.emit("// Calibracao entre ferramentas concluida.")
        elif word == "CALIBRATE_IDEX_CANCEL":
            self.gcode_response.emit("// action:prompt_end")
            self.state[machine.ALIGN_VARS].update(active=0, origin_set=0)
            self.gcode_response.emit("// Calibracao interrompida. Nada foi gravado.")
        elif word.startswith("CALIBRATE_IDEX") or word == "IDEX_Z_TRIM_T1":
            self.gcode_response.emit(f"// {word}: simulado")
        return None

    def _next_screw(self, accepted: bool) -> None:
        screws = self.state["bed_screws"]
        screws["accepted_screws"] = screws["accepted_screws"] + 1 if accepted else 0
        if screws["accepted_screws"] >= 3:
            screws.update(is_active=False)
        else:
            screws["current_screw"] = (screws["current_screw"] + 1) % 3

    def _go_to_camera(self, tool: int) -> None:
        """Park the nozzle a little off centre, then show the prompt of the macros."""
        toolhead = self.state["toolhead"]
        toolhead["homed_axes"] = "xyz"
        off_x, off_y = CAMERA_START_OFFSET[tool]
        toolhead["position"] = [CAMERA_CENTER[0] + off_x, CAMERA_CENTER[1] + off_y, 6.7, 0.0]
        self._run_line(f"T{tool}")
        for line in (
            "// action:prompt_begin Calibracao X/Y manual",
            f"// action:prompt_text Bico T{tool}: move a cabeca ate o furo do bico ficar "
            "no centro da mira. Depois carrega em Seguinte.",
            "// action:prompt_button_group_start",
            "// action:prompt_button X −0.10|_ALIGN_JOG X=-0.10|info",
            "// action:prompt_button X +0.10|_ALIGN_JOG X=0.10|info",
            "// action:prompt_button_group_end",
            "// action:prompt_footer_button Cancelar|CALIBRATE_IDEX_CANCEL|error",
            "// action:prompt_footer_button Seguinte|CALIBRATE_IDEX_NEXT|primary",
            "// action:prompt_show",
        ):
            self.gcode_response.emit(line)

    # --- simulated time -------------------------------------------------
    def _start_print(self, filename: str) -> None:
        self._print_clock = 0.0
        self.state["print_stats"].update(
            state="printing", filename=filename, print_duration=0.0
        )
        self.state["virtual_sdcard"]["progress"] = 0.0
        self.state["display_status"]["message"] = machine.PREPARE_STAGES[0][0]

    def _tick(self) -> None:
        dt = TICK_MS / 1000 * self.speed
        for name in machine.EXTRUDERS.values():
            heater = self.state[name]
            goal = heater["target"] or 22.0
            heater["temperature"] += (goal - heater["temperature"]) * min(dt * 0.15, 1.0)
        if self.state["print_stats"]["state"] == "printing":
            self._advance_print(dt)
        self.status.emit({k: self.state[k] for k in (
            "extruder", "extruder1", "print_stats", "virtual_sdcard", "display_status"
        )})

    def _advance_print(self, dt: float) -> None:
        self._print_clock += dt
        stage = int(self._print_clock / STAGE_SECONDS)
        if stage < len(machine.PREPARE_STAGES):
            self.state["display_status"]["message"] = machine.PREPARE_STAGES[stage][0]
            return
        self.state["display_status"]["message"] = machine.PRINTING_MESSAGE
        stats = self.state["print_stats"]
        stats["print_duration"] += dt
        progress = min(stats["print_duration"] / PRINT_SECONDS, 1.0)
        self.state["virtual_sdcard"]["progress"] = progress
        stats["info"] = {"current_layer": max(int(progress * 40), 1), "total_layer": 40}
        if progress >= 1.0:
            stats["state"] = "complete"
