#!/bin/bash
# Muda de ecra por SSH. Uso: ecra.sh mbind | klipperscreen | estado
# Pede ao Moonraker, por isso nao precisa de sudo.
BOOT_FILE="$HOME/.config/mbind-screen/boot-screen"
MOONRAKER="http://localhost:7125"

state() {
    for service in MBindScreen KlipperScreen; do
        printf '%-14s %s\n' "$service" "$(systemctl is-active "$service")"
    done
    printf '%-14s %s\n' "No arranque" "$(cat "$BOOT_FILE" 2>/dev/null || echo klipperscreen)"
}

switch() {
    mkdir -p "$(dirname "$BOOT_FILE")"
    echo "$1" > "$BOOT_FILE"
    curl -fsS -X POST "$MOONRAKER/machine/services/start?service=$2" > /dev/null \
        || sudo systemctl --no-block start "$2.service" \
        || { echo "Nao foi possivel arrancar o $2."; exit 1; }
    echo "A mudar para $2."
}

case "${1:-estado}" in
    mbind) switch mbind MBindScreen ;;
    klipperscreen) switch klipperscreen KlipperScreen ;;
    estado) state ;;
    *) echo "Uso: $0 mbind | klipperscreen | estado"; exit 1 ;;
esac
