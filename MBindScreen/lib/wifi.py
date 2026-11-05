"""Wi-Fi through NetworkManager's nmcli, without blocking the screen.

The screen's link to Moonraker is local, so changing network does not touch it.
The password goes on the nmcli command line, as nmcli has no other reliable way
without a terminal: it must never reach the log.
"""
from __future__ import annotations

import dataclasses
import logging
import typing

from PyQt6 import QtCore

logger = logging.getLogger(__name__)
NMCLI = "nmcli"
TIMEOUT_MS = 45000  # a connection attempt can take this long
WIFI_PROFILE = "802-11-wireless"
OPEN_NETWORK = ("", "--")
MINIMUM_PASSWORD = 8  # WPA

DEVICES = ("-t", "-f", "DEVICE,TYPE", "device", "status")
PROFILES = ("-t", "-f", "NAME,TYPE", "connection", "show")
NETWORKS = ("-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list")

Callback = typing.Callable[[bool, str], None]


@dataclasses.dataclass(frozen=True)
class Network:
    ssid: str
    signal: int
    secured: bool
    in_use: bool


def split_fields(line: str) -> list[str]:
    """nmcli -t separates with ":" and writes a real ":" as "\\:"."""
    fields, current, escaped = [], "", False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append(current)
            current = ""
        else:
            current += char
    return [*fields, current]


def parse_networks(output: str) -> list[Network]:
    """One entry per name: a network has several access points. Current one first."""
    best: dict[str, Network] = {}
    for line in output.splitlines():
        fields = split_fields(line)
        if len(fields) != 4 or not fields[1].strip():  # hidden networks have no name
            continue
        in_use, ssid, signal, security = fields
        found = Network(
            ssid,
            int(signal) if signal.isdigit() else 0,
            security not in OPEN_NETWORK,
            in_use == "*",
        )
        known = best.get(ssid)
        if known:
            found = dataclasses.replace(
                found,
                signal=max(known.signal, found.signal),
                in_use=known.in_use or found.in_use,
            )
        best[ssid] = found
    return sorted(best.values(), key=lambda n: (not n.in_use, -n.signal, n.ssid.lower()))


def wifi_device(output: str) -> typing.Optional[str]:
    for line in output.splitlines():
        fields = split_fields(line)
        if len(fields) == 2 and fields[1] == "wifi":
            return fields[0]
    return None


def wifi_profiles(output: str) -> list[str]:
    fields = (split_fields(line) for line in output.splitlines())
    return [f[0] for f in fields if len(f) == 2 and f[1] == WIFI_PROFILE]


def address_args(device: str) -> tuple[str, ...]:
    return ("-e", "no", "-g", "IP4.ADDRESS", "device", "show", device)


def profile_ssid_args(name: str) -> tuple[str, ...]:
    return ("-e", "no", "-g", "802-11-wireless.ssid", "connection", "show", name)


def join_profile_args(name: str) -> tuple[str, ...]:
    return ("connection", "up", name)


def join_args(ssid: str, password: str = "") -> tuple[str, ...]:
    args = ("device", "wifi", "connect", ssid)
    return (*args, "password", password) if password else args


class Nmcli(QtCore.QObject):
    def run(self, args: typing.Sequence[str], callback: Callback) -> None:
        """``callback(ok, output)`` always runs once. ``args`` may hold a password."""
        process = QtCore.QProcess(self)
        timer = QtCore.QTimer(process)
        timer.setSingleShot(True)
        timer.timeout.connect(process.kill)
        answered = []

        def finish(ok: bool) -> None:
            if answered:
                return
            answered.append(True)
            timer.stop()
            output = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
            process.deleteLater()
            callback(ok, output)

        process.finished.connect(lambda code, _status: finish(code == 0))
        process.errorOccurred.connect(
            lambda error: error == QtCore.QProcess.ProcessError.FailedToStart and finish(False)
        )
        timer.start(TIMEOUT_MS)
        process.start(NMCLI, list(args))
