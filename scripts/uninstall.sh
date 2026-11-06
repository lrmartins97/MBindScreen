#!/bin/bash
# Deixa a maquina como estava antes do MBindScreen, tenha sido so' experimentado ou
# instalado: servicos, Moonraker, pacotes novos, ambiente Python, logs e o proprio codigo.
# So' remove os pacotes que o MBindScreen instalou (ver comum.sh). KlipperScreen fica.
set -uo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
APP_DIR="$(dirname "$SCRIPT_DIR")"
ENV_DIR="${MBINDSCREEN_ENV:-$HOME/.MBindScreen-env}"
ASVC="$HOME/printer_data/moonraker.asvc"
CONFIG_DIR="$HOME/printer_data/config"
UNIT_DIR="${MBINDSCREEN_UNIT_DIR:-/etc/systemd/system}"
TRIAL_UNIT=MBindScreen-try.service
PENDING=()
# shellcheck source=comum.sh
source "$SCRIPT_DIR/comum.sh"

in_config_git() {
    git -C "$CONFIG_DIR" show "HEAD:$1" 2> /dev/null
}

remove_services() {
    local installed=no
    [ -f "$UNIT_DIR/MBindScreen.service" ] && installed=yes
    [ -f "$UNIT_DIR/mbind-screen-boot.service" ] && installed=yes
    sudo rm -f "$UNIT_DIR/KlipperScreen.service.d/mbind-screen.conf"
    sudo rmdir "$UNIT_DIR/KlipperScreen.service.d" 2> /dev/null
    echo "A remover os servicos"
    sudo systemctl stop "$TRIAL_UNIT" 2> /dev/null
    sudo systemctl reset-failed "$TRIAL_UNIT" 2> /dev/null
    sudo rm -f "/run/systemd/system/$TRIAL_UNIT"
    if [ "$installed" = yes ]; then
        sudo systemctl disable mbind-screen-boot.service 2> /dev/null
        sudo systemctl stop MBindScreen.service 2> /dev/null
        sudo rm -f "$UNIT_DIR/MBindScreen.service" "$UNIT_DIR/mbind-screen-boot.service"
    fi
    sudo systemctl daemon-reload
    # O install.sh desativou-o; a experiencia nao.
    [ "$installed" = no ] || sudo systemctl enable KlipperScreen.service
    sudo systemctl start --no-block KlipperScreen.service
    # O perfil do hotspot foi criado pelo ecra. As outras redes sao da maquina.
    nmcli connection delete MBind-hotspot > /dev/null 2>&1
}

remove_update_manager_block() {
    local file="$CONFIG_DIR/moonraker.conf" cleaned
    cleaned="$(awk '
        /^\[update_manager MBindScreen\]/ { skip = 1; blanks = 0; next }
        skip { if ($0 ~ /^\[/ || $0 ~ /^[[:space:]]*$/) skip = 0; else next }
        /^[[:space:]]*$/ { blanks++; next }
        { while (blanks > 0) { print ""; blanks-- } print }
    ' "$file")"
    printf '%s\n' "$cleaned" > "$file"  # mantem dono, permissoes e links
}

# O botao do atalho-ecra.sh
remove_screen_menu() {
    local file="$CONFIG_DIR/KlipperScreen.conf" cleaned
    [ -f "$file" ] && grep -q "^\[menu __main more mbindscreen\]" "$file" || return 0
    cleaned="$(awk '
        /^\[menu __main more mbindscreen\]/ { skip = 1; next }
        skip { if ($0 ~ /^[[:space:]]*$/) skip = 0; next }
        { print }
    ' "$file"; echo x)"
    printf '%s' "${cleaned%x}" > "$file"
    sudo systemctl restart KlipperScreen.service
}

remove_from_moonraker() {
    local changed=no conf="$CONFIG_DIR/moonraker.conf"
    if [ -f "$ASVC" ] && grep -qx "MBindScreen" "$ASVC"; then
        sed -i '/^MBindScreen$/d' "$ASVC"
        changed=yes
    fi
    if [ -f "$conf" ] && grep -q "^\[update_manager MBindScreen\]" "$conf"; then
        if in_config_git moonraker.conf | grep -q "update_manager MBindScreen"; then
            PENDING+=("moonraker.conf: o bloco [update_manager MBindScreen] esta no git da"
                      "configuracao e ficou. Tira-o no repositorio m-bind-config.")
        else
            remove_update_manager_block
            changed=yes
        fi
    fi
    if [ "$changed" = yes ]; then
        echo "A reiniciar o Moonraker"
        sudo systemctl restart moonraker
    fi
}

# O apt arrastaria o que depende destes pacotes. Se for preciso mais alguma coisa alem do
# que o MBindScreen trouxe, algo novo passou a usa-los: ficam, e diz-se quais.
remove_packages() {
    [ -f "$PACKAGES_RECORD" ] || return 0
    local packages affected others list
    packages="$(LC_ALL=C comm -12 <(LC_ALL=C sort -u "$PACKAGES_RECORD") <(installed_packages))"
    [ -n "$packages" ] || return 0
    list="$(echo "$packages" | tr '\n' ' ')"
    echo "A remover os pacotes que o MBindScreen instalou: $list"
    # shellcheck disable=SC2086
    affected="$(LC_ALL=C apt-get -s purge $packages | awk '/^(Purg|Remv) / { print $2 }' \
        | sed 's/:.*//' | LC_ALL=C sort -u)"
    others="$(LC_ALL=C comm -13 <(echo "$packages") <(echo "$affected"))"
    if [ -n "$others" ]; then
        PENDING+=("Pacotes nao removidos, porque levariam tambem: $(echo "$others" | tr '\n' ' ')"
                  "Remover a mao, se fizer sentido: sudo apt-get purge $list")
        return 0
    fi
    # shellcheck disable=SC2086
    sudo apt-get purge -y $packages || PENDING+=("Pacotes por remover: sudo apt-get purge $list")
}

remove_files() {
    echo "A remover os ficheiros"
    [ -f "$ENV_DIR/pyvenv.cfg" ] && rm -rf "$ENV_DIR"
    rm -rf "$(dirname "$PACKAGES_RECORD")"
    rm -f "$HOME"/printer_data/logs/MBindScreen.log* \
        "$HOME/printer_data/logs/MBindScreen_fault.log"
    if [ -f "$CONFIG_DIR/MBindScreen.cfg" ]; then
        if [ -n "$(in_config_git MBindScreen.cfg)" ]; then
            PENDING+=("MBindScreen.cfg esta no git da configuracao e ficou.")
        else
            rm -f "$CONFIG_DIR/MBindScreen.cfg"
        fi
    fi
    [ -f "$APP_DIR/MBindScreen/MBindScreen.py" ] && rm -rf "$APP_DIR"
}

# Tudo dentro de main: este ficheiro apaga-se a si proprio a meio.
main() {
    [ "$(id -u)" -ne 0 ] || fail "Corre como o utilizador da impressora, sem sudo."
    refuse_if_busy
    cd "$HOME" || fail "Sem acesso a $HOME"
    remove_services
    remove_from_moonraker
    remove_screen_menu
    remove_packages
    remove_files
    echo
    if [ "${#PENDING[@]}" -gt 0 ]; then
        printf '\033[0;33mFicou por fazer:\033[0m\n'
        printf '  %s\n' "${PENDING[@]}"
    fi
    echo "MBindScreen removido. KlipperScreen no ecra."
    exit 0
}

main
