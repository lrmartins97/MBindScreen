#!/bin/bash
# Experimenta o MBindScreen sem instalar nada de permanente. Ver docs/experimentar-na-maquina.md
#
#   experimentar.sh preparar         uma vez: pacotes e ambiente Python
#   experimentar.sh ver [minutos]    mostra o ecra, sem enviar comandos a maquina (10 min)
#   experimentar.sh usar [minutos]   os botoes atuam mesmo na maquina (10 min)
#   experimentar.sh parar            volta ao KlipperScreen ja
#   experimentar.sh estado           diz o que esta a correr
#
# Para tirar tudo da maquina: scripts/uninstall.sh
# Nao toca no arranque da maquina, no Moonraker, nem em printer_data. O servico fica
# em /run e desaparece ao reiniciar: uma falha de luz volta ao KlipperScreen.
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
APP_DIR="$(dirname "$SCRIPT_DIR")"
ENV_DIR="${MBINDSCREEN_ENV:-$HOME/.MBindScreen-env}"
UNIT=MBindScreen-try
UNIT_FILE="/run/systemd/system/$UNIT.service"
DEFAULT_MINUTES=10
MAX_MINUTES=120
# shellcheck source=comum.sh
source "$SCRIPT_DIR/comum.sh"

prepare() {
    refuse_if_busy
    echo "A instalar bibliotecas (nao atualiza o que ja esta instalado)..."
    install_missing_packages "$SCRIPT_DIR/system-dependencies.json"
    echo "A preparar o ambiente Python em $ENV_DIR..."
    [ -x "$ENV_DIR/bin/python" ] || python3 -m venv "$ENV_DIR"
    "$ENV_DIR/bin/pip" install --disable-pip-version-check --no-cache-dir -q -r "$SCRIPT_DIR/requirements.txt"
    QT_QPA_PLATFORM=offscreen "$ENV_DIR/bin/python" -c \
        "from PyQt6 import QtSvg, QtWebSockets, QtWidgets; print('PyQt6 OK')"
    echo "Pronto. A seguir: bash $0 ver"
}

start() {
    local mode_args="$1" minutes="${2:-$DEFAULT_MINUTES}" group_line=""
    case "$minutes" in ''|*[!0-9]*|0) fail "Os minutos tem de ser um numero." ;; esac
    [ "$minutes" -le "$MAX_MINUTES" ] || fail "No maximo $MAX_MINUTES minutos de cada vez."
    [ -x "$ENV_DIR/bin/python" ] || fail "Corre primeiro: bash $0 preparar"
    [ -f /etc/systemd/system/KlipperScreen.service ] || fail "KlipperScreen nao encontrado."
    refuse_if_busy
    getent group klipperscreen > /dev/null && group_line="SupplementaryGroups=klipperscreen"
    sed -e "s|MBS_GROUP_LINE|$group_line|" -e "s|MBS_SECONDS|$((minutes * 60))|" \
        -e "s|MBS_MODE_ARGS|$mode_args|" -e "s|MBS_USER|$USER|g" -e "s|MBS_UID|$(id -u)|g" \
        -e "s|MBS_DIR|$APP_DIR|g" -e "s|MBS_ENV|$ENV_DIR|g" \
        "$SCRIPT_DIR/MBindScreen-try.service" | sudo tee "$UNIT_FILE" > /dev/null
    sudo systemctl daemon-reload
    sudo systemctl reset-failed "$UNIT" 2> /dev/null || true
    sudo systemctl start --no-block "$UNIT"
    echo "MBindScreen no ecra durante $minutes minutos; depois volta o KlipperScreen."
    echo "Voltar antes: Definicoes > Ecra, ou: bash $0 parar"
}

stop() {
    sudo systemctl stop "$UNIT" 2> /dev/null || true
    sudo systemctl start --no-block KlipperScreen.service
    echo "De volta ao KlipperScreen."
}

state() {
    printf '%-16s %s\n' "$UNIT" "$(systemctl is-active "$UNIT" 2> /dev/null || true)"
    printf '%-16s %s\n' KlipperScreen "$(systemctl is-active KlipperScreen 2> /dev/null || true)"
    printf '%-16s %s\n' "No arranque" "KlipperScreen ($(systemctl is-enabled KlipperScreen))"
    echo "Log: ~/printer_data/logs/MBindScreen.log  ou  journalctl -u $UNIT -n 50 --no-pager"
}

case "${1:-}" in
    preparar) prepare ;;
    ver) start --read-only "${2:-}" ;;
    usar) start "" "${2:-}" ;;
    parar) stop ;;
    estado) state ;;
    *) sed -n '2,9p' "$0" | sed 's/^# \?//'; exit 1 ;;
esac
