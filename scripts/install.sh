#!/bin/bash
# Instala o MBindScreen ao lado do KlipperScreen. O ecra que esta a funcionar nao
# muda: depois escolhe-se com o botao no KlipperScreen ou com scripts/ecra.sh.
# Uso: bash ~/MBindScreen/scripts/install.sh
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
APP_DIR="$(dirname "$SCRIPT_DIR")"
ENV_DIR="${MBINDSCREEN_ENV:-$HOME/.MBindScreen-env}"
ASVC="$HOME/printer_data/moonraker.asvc"
MOONRAKER_CONF="$HOME/printer_data/config/moonraker.conf"
UNIT_DIR=/etc/systemd/system
# shellcheck source=comum.sh
source "$SCRIPT_DIR/comum.sh"

info() { printf '\033[0;36m%s\033[0m\n' "$1"; }

check_requirements() {
    [ "$(id -u)" -ne 0 ] || fail "Corre como o utilizador da impressora, sem sudo."
    [ -f "$UNIT_DIR/KlipperScreen.service" ] \
        || fail "KlipperScreen nao encontrado: e' preciso o X e o servico dele."
    [ -f "$ASVC" ] || fail "$ASVC nao encontrado: o Moonraker esta instalado?"
    refuse_if_busy  # o Moonraker reinicia
}

install_packages() {
    info "A instalar pacotes do sistema"
    install_missing_packages "$SCRIPT_DIR/system-dependencies.json"
}

install_virtualenv() {
    info "A preparar o ambiente Python em $ENV_DIR"
    [ -x "$ENV_DIR/bin/python" ] || python3 -m venv "$ENV_DIR"
    "$ENV_DIR/bin/pip" install --disable-pip-version-check --no-cache-dir -q -r "$SCRIPT_DIR/requirements.txt"
    QT_QPA_PLATFORM=offscreen "$ENV_DIR/bin/python" -c \
        "from PyQt6 import QtSvg, QtWebSockets, QtWidgets; print('PyQt6 OK')"
}

fill_template() {
    local group_line=""
    getent group klipperscreen > /dev/null && group_line="SupplementaryGroups=klipperscreen"
    sed -e "s|MBS_GROUP_LINE|$group_line|" -e "s|MBS_USER|$USER|g" -e "s|MBS_HOME|$HOME|g" \
        -e "s|MBS_DIR|$APP_DIR|g" -e "s|MBS_ENV|$ENV_DIR|g" "$1"
}

install_services() {
    info "A instalar os servicos"
    fill_template "$SCRIPT_DIR/MBindScreen.service" \
        | sudo tee "$UNIT_DIR/MBindScreen.service" > /dev/null
    fill_template "$SCRIPT_DIR/mbind-screen-boot.service" \
        | sudo tee "$UNIT_DIR/mbind-screen-boot.service" > /dev/null
    sudo systemctl daemon-reload
    # A partir de agora e' o mbind-screen-boot que escolhe o ecra. O KlipperScreen
    # nao e' parado: continua no ecra ate alguem mudar.
    sudo systemctl disable KlipperScreen.service
    sudo systemctl enable mbind-screen-boot.service
}

allow_in_moonraker() {
    if ! grep -qx "MBindScreen" "$ASVC"; then
        info "A autorizar o servico no Moonraker"
        [ -z "$(tail -c 1 "$ASVC")" ] || echo >> "$ASVC"
        echo MBindScreen >> "$ASVC"
    fi
}

add_update_manager() {
    if grep -q "update_manager MBindScreen" "$MOONRAKER_CONF"; then
        return
    fi
    info "A acrescentar o MBindScreen ao moonraker.conf"
    local origin branch
    origin="$(git -C "$APP_DIR" remote get-url origin)"
    branch="$(git -C "$APP_DIR" rev-parse --abbrev-ref HEAD)"
    cat >> "$MOONRAKER_CONF" <<EOF

[update_manager MBindScreen]
type: git_repo
path: $APP_DIR
origin: $origin
primary_branch: $branch
virtualenv: $ENV_DIR
requirements: scripts/requirements.txt
system_dependencies: scripts/system-dependencies.json
is_system_service: False
EOF
}

check_moonraker_services() {
    local info="" attempt
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        info="$(curl -fsS http://localhost:7125/machine/system_info 2>/dev/null || true)"
        [ -n "$info" ] && break
        sleep 2
    done
    for service in KlipperScreen MBindScreen; do
        case "$info" in
            *"\"$service\""*) ;;
            *) printf '\033[0;33mAviso: o Moonraker nao ve o servico %s.\033[0m\n' "$service" ;;
        esac
    done
}

check_requirements
install_packages
install_virtualenv
install_services
allow_in_moonraker
add_update_manager
info "A reiniciar o Moonraker"
sudo systemctl restart moonraker
check_moonraker_services

cat <<EOF

MBindScreen instalado. O ecra continua no KlipperScreen.
  Experimentar:     bash $SCRIPT_DIR/ecra.sh mbind
  Voltar:           bash $SCRIPT_DIR/ecra.sh klipperscreen   (ou Definicoes > Ecra)
  Ver o estado:     bash $SCRIPT_DIR/ecra.sh estado
  Log:              ~/printer_data/logs/MBindScreen.log (tambem no Mainsail)
EOF
