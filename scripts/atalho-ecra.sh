#!/bin/bash
# Botao "MBindScreen" no menu Mais do KlipperScreen, para saltar para este ecra sem
# linha de comandos. O arranque nao muda: a maquina continua a ligar no KlipperScreen.
#
#   atalho-ecra.sh instalar     acrescenta o botao
#   atalho-ecra.sh remover      volta a deixar tudo como estava
#
# O Moonraker so' autoriza servicos ja carregados quando arranca. O ficheiro em
# KlipperScreen.service.d faz o systemd carregar o MBindScreen.service sempre.
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
APP_DIR="$(dirname "$SCRIPT_DIR")"
ENV_DIR="${MBINDSCREEN_ENV:-$HOME/.MBindScreen-env}"
UNIT_DIR="${MBINDSCREEN_UNIT_DIR:-/etc/systemd/system}"
ASVC="$HOME/printer_data/moonraker.asvc"
SCREEN_CONF="$HOME/printer_data/config/KlipperScreen.conf"
DROP_IN="$UNIT_DIR/KlipperScreen.service.d/mbind-screen.conf"
MENU_SECTION="[menu __main more mbindscreen]"
# shellcheck source=comum.sh
source "$SCRIPT_DIR/comum.sh"

menu_block() {
    cat <<EOF
$MENU_SECTION
name: MBindScreen
icon: settings
method: machine.services.start
params: {"service": "MBindScreen"}
confirm: Mudar para o ecra MBindScreen?

EOF
}

add_menu() {
    grep -qF "$MENU_SECTION" "$SCREEN_CONF" && return 0
    local block
    block="$(menu_block; echo x)"
    block="${block%x}"
    # Antes da zona que o KlipperScreen escreve sozinho
    BLOCK="$block" awk '
        !done && /^#~#/ { printf "%s", ENVIRON["BLOCK"]; done = 1 }
        { print }
        END { if (!done) printf "%s", ENVIRON["BLOCK"] }
    ' "$SCREEN_CONF" > "$SCREEN_CONF.mbind-tmp"
    cat "$SCREEN_CONF.mbind-tmp" > "$SCREEN_CONF"
    rm -f "$SCREEN_CONF.mbind-tmp"
}

remove_menu() {
    [ -f "$SCREEN_CONF" ] && grep -qF "$MENU_SECTION" "$SCREEN_CONF" || return 0
    awk -v section="$MENU_SECTION" '
        $0 == section { skip = 1; next }
        skip { if ($0 ~ /^[[:space:]]*$/) skip = 0; next }
        { print }
    ' "$SCREEN_CONF" > "$SCREEN_CONF.mbind-tmp"
    cat "$SCREEN_CONF.mbind-tmp" > "$SCREEN_CONF"
    rm -f "$SCREEN_CONF.mbind-tmp"
}

install_shortcut() {
    local group_line=""
    [ -x "$ENV_DIR/bin/python" ] || fail "Corre primeiro: bash $SCRIPT_DIR/experimentar.sh preparar"
    refuse_if_busy
    getent group klipperscreen > /dev/null && group_line="SupplementaryGroups=klipperscreen"
    sed -e "s|MBS_GROUP_LINE|$group_line|" -e "s|MBS_USER|$(id -un)|g" -e "s|MBS_HOME|$HOME|g" \
        -e "s|MBS_DIR|$APP_DIR|g" -e "s|MBS_ENV|$ENV_DIR|g" "$SCRIPT_DIR/MBindScreen.service" \
        | sudo tee "$UNIT_DIR/MBindScreen.service" > /dev/null
    sudo mkdir -p "$(dirname "$DROP_IN")"
    printf '[Unit]\nConflicts=MBindScreen.service\n' | sudo tee "$DROP_IN" > /dev/null
    sudo systemctl daemon-reload
    grep -qx "MBindScreen" "$ASVC" || {
        [ -z "$(tail -c 1 "$ASVC")" ] || echo >> "$ASVC"
        echo MBindScreen >> "$ASVC"
    }
    add_menu
    sudo systemctl restart moonraker
    sudo systemctl restart KlipperScreen
    echo "Pronto: KlipperScreen > Mais > MBindScreen. Voltar: Definicoes, com o codigo."
}

remove_shortcut() {
    refuse_if_busy
    sudo systemctl stop MBindScreen.service 2> /dev/null || true
    sudo rm -f "$UNIT_DIR/MBindScreen.service" "$DROP_IN"
    sudo rmdir "$(dirname "$DROP_IN")" 2> /dev/null || true
    sudo systemctl daemon-reload
    remove_menu
    [ ! -f "$ASVC" ] || sed -i '/^MBindScreen$/d' "$ASVC"
    sudo systemctl restart moonraker
    sudo systemctl restart KlipperScreen
    echo "Botao removido. KlipperScreen como estava."
}

case "${1:-}" in
    instalar) install_shortcut ;;
    remover) remove_shortcut ;;
    *) sed -n 2,7p "$0" | sed 's/^# \?//'; exit 1 ;;
esac
