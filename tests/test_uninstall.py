"""uninstall.sh and the package record, run in bash against fake system commands."""
import json
import pathlib
import shutil
import stat
import subprocess
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GIT_BASH = pathlib.Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH, reason="needs bash")
UNINSTALL = (
    'export MBINDSCREEN_UNIT_DIR="$HOME/units"; '
    'bash "$HOME/MBindScreen/scripts/uninstall.sh"'
)
PREPARE = (
    'source "$HOME/MBindScreen/scripts/comum.sh"; '
    'install_missing_packages "$FAKE/deps.json"'
)
BLOCK = """[update_manager MBindScreen]
type: git_repo
path: ~/MBindScreen
is_system_service: False
"""
STUBS = {
    "sudo": 'exec "$@"',
    "systemctl": 'echo "systemctl $*" >> "$FAKE/calls"',
    "curl": 'cat "$FAKE/moonraker" 2>/dev/null || exit 7',
    "git": 'last="${@: -1}"; cat "$FAKE/git-${last#HEAD:}" 2>/dev/null || exit 1',
    "dpkg-query": 'sed "s/^/ii  /" "$FAKE/installed"',
    "id": "echo 1000",
    "apt-get": r"""
echo "apt-get $*" >> "$FAKE/calls"
case "$*" in
  *-s\ purge*) cat "$FAKE/simulation" 2>/dev/null || true ;;
  *purge*) for p in "$@"; do sed -i "/^$p\$/d" "$FAKE/installed"; done ;;
  *install*) cat "$FAKE/pulled-in" >> "$FAKE/installed" ;;
esac
""",
}
DRIVER = r"""
to_unix() { cygpath -u "$1" 2>/dev/null || echo "$1"; }
export HOME="$(to_unix "$1")" FAKE="$(to_unix "$2")" PATH="$(to_unix "$3"):$PATH"
eval "$4"
"""


@pytest.fixture
def machine(tmp_path):
    home = tmp_path / "home"
    fake = tmp_path / "fake"
    stubs = tmp_path / "stubs"
    data = home / "printer_data"
    for folder in (data / "config", data / "logs", fake, stubs,
                   home / ".config/mbind-screen", home / ".MBindScreen-env"):
        folder.mkdir(parents=True)
    app = home / "MBindScreen"
    shutil.copytree(ROOT / "scripts", app / "scripts")
    (app / "MBindScreen").mkdir()
    (app / "MBindScreen/MBindScreen.py").write_text("")
    (home / ".MBindScreen-env/pyvenv.cfg").write_text("")
    (home / ".config/mbind-screen/boot-screen").write_text("mbind\n")
    for name in ("MBindScreen.log", "MBindScreen.log.1", "MBindScreen_fault.log", "klippy.log"):
        (data / "logs" / name).write_text("x")
    (data / "moonraker.asvc").write_bytes(b"klipper\nMBindScreen\n")
    (data / "config/MBindScreen.cfg").write_text("")
    (data / "config/moonraker.conf").write_bytes(b"[server]\nport: 7125\n\n" + BLOCK.encode())
    python = pathlib.Path(sys.executable).as_posix()
    for name, body in {**STUBS, "python3": f'exec "{python}" "$@"'}.items():
        path = stubs / name
        path.write_bytes(f"#!/bin/bash\n{body}\n".encode())
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    (fake / "installed").write_bytes(b"bash\nxinit\n")
    (fake / "calls").write_text("")
    return types.SimpleNamespace(home=home, data=data, fake=fake, app=app, stubs=stubs)


def run(machine, command):
    """Run with the fake commands first on PATH and HOME in the temporary folder."""
    return subprocess.run(
        [BASH, "-c", DRIVER, "driver", str(machine.home), str(machine.fake),
         str(machine.stubs), command],
        check=False, capture_output=True, encoding="utf-8", timeout=60,
    )


def calls(machine):
    return (machine.fake / "calls").read_text()


def record(machine):
    return machine.home / ".config/mbind-screen/pacotes-instalados"


def test_removes_everything_of_ours_and_nothing_else(machine):
    record(machine).write_bytes(b"libnew\nxinit-dep\n")
    (machine.fake / "installed").write_bytes(b"bash\nlibnew\nxinit\nxinit-dep\n")
    (machine.fake / "simulation").write_bytes(b"Purg libnew [1]\nPurg xinit-dep:arm64 [1]\n")
    done = run(machine, UNINSTALL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not machine.app.exists()
    assert not (machine.home / ".MBindScreen-env").exists()
    assert not (machine.home / ".config/mbind-screen").exists()
    assert not (machine.data / "config/MBindScreen.cfg").exists()
    assert [p.name for p in (machine.data / "logs").iterdir()] == ["klippy.log"]
    assert (machine.data / "moonraker.asvc").read_bytes() == b"klipper\n"
    assert (machine.data / "config/moonraker.conf").read_bytes() == b"[server]\nport: 7125\n"
    assert (machine.fake / "installed").read_bytes() == b"bash\nxinit\n"
    assert "systemctl restart moonraker" in calls(machine)
    assert "start --no-block KlipperScreen" in calls(machine)


def test_a_section_after_the_block_survives(machine):
    conf = machine.data / "config/moonraker.conf"
    conf.write_bytes(f"[a]\nx: 1\n\n{BLOCK}\n[b]\ny: 2\n".encode())
    assert run(machine, UNINSTALL).returncode == 0
    assert conf.read_bytes() == b"[a]\nx: 1\n\n[b]\ny: 2\n"


def test_a_trial_leaves_moonraker_and_klipperscreen_boot_alone(machine):
    (machine.data / "config/moonraker.conf").write_bytes(b"[server]\n")
    (machine.data / "moonraker.asvc").write_bytes(b"klipper\n")
    assert run(machine, UNINSTALL).returncode == 0
    assert "restart moonraker" not in calls(machine)
    assert "enable KlipperScreen" not in calls(machine)
    assert "stop MBindScreen-try.service" in calls(machine)
    assert not machine.app.exists()


def test_undoes_the_full_install(machine):
    units = machine.home / "units"
    units.mkdir()
    (units / "MBindScreen.service").write_text("")
    (units / "mbind-screen-boot.service").write_text("")
    assert run(machine, UNINSTALL).returncode == 0
    assert not list(units.iterdir())
    assert "disable mbind-screen-boot.service" in calls(machine)
    assert "enable KlipperScreen.service" in calls(machine)


def test_package_something_else_needs_is_kept_and_reported(machine):
    record(machine).write_bytes(b"libnew\n")
    (machine.fake / "installed").write_bytes(b"bash\nlibnew\nother-app\n")
    (machine.fake / "simulation").write_bytes(b"Purg libnew [1]\nPurg other-app [1]\n")
    done = run(machine, UNINSTALL)
    assert done.returncode == 0
    assert "other-app" in done.stdout and "sudo apt-get purge libnew" in done.stdout
    assert "libnew" in (machine.fake / "installed").read_text()
    assert "purge -y" not in calls(machine)


def test_without_a_record_no_package_is_touched(machine):
    assert run(machine, UNINSTALL).returncode == 0
    assert "apt-get" not in calls(machine)


@pytest.mark.parametrize(
    "reply", ['{"state": "printing"}', '{"state": "Printing"}', '{"state": "paused"}']
)
def test_refuses_while_the_machine_works(machine, reply):
    (machine.fake / "moonraker").write_text(reply)
    assert run(machine, UNINSTALL).returncode != 0
    assert machine.app.exists()
    assert calls(machine) == ""


def test_config_in_git_is_left_for_that_repository(machine):
    (machine.fake / "git-moonraker.conf").write_text("[update_manager MBindScreen]\n")
    (machine.fake / "git-MBindScreen.cfg").write_text("[screen]\n")
    done = run(machine, UNINSTALL)
    assert done.returncode == 0
    conf = machine.data / "config/moonraker.conf"
    assert "update_manager MBindScreen" in conf.read_text()
    assert (machine.data / "config/MBindScreen.cfg").exists()
    assert "m-bind-config" in done.stdout


def test_install_records_only_what_is_new(machine):
    (machine.fake / "deps.json").write_text(json.dumps({"debian": ["xinit", "libnew"]}))
    (machine.fake / "pulled-in").write_bytes(b"libnew\nlibdep\n")
    done = run(machine, PREPARE)
    assert done.returncode == 0, done.stdout + done.stderr
    assert record(machine).read_text().split() == ["libdep", "libnew"]
    install = calls(machine).strip()
    assert install.endswith(" libnew") and "xinit" not in install
    assert "--no-upgrade" in install and "--no-install-recommends" in install


def test_a_failed_install_still_records_what_arrived(machine):
    (machine.fake / "deps.json").write_text(json.dumps({"debian": ["libnew"]}))
    (machine.fake / "pulled-in").write_bytes(b"libnew\n")
    stub = machine.stubs / "sudo"
    stub.write_bytes(b'#!/bin/bash\n"$@"\nexit 100\n')
    assert run(machine, PREPARE).returncode == 100
    assert record(machine).read_text() == "libnew\n"


def test_a_second_preparation_installs_nothing_and_keeps_the_record(machine):
    (machine.fake / "deps.json").write_text(json.dumps({"debian": ["xinit"]}))
    record(machine).write_bytes(b"libnew\n")
    assert run(machine, PREPARE).returncode == 0
    assert record(machine).read_text() == "libnew\n"
    assert "apt-get" not in calls(machine)
