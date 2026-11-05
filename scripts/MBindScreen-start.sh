#!/bin/bash
# Arrancado pelo servico MBindScreen. Regista este ecra para o proximo arranque da
# maquina (assim, mudar para aqui a partir do KlipperScreen tambem fica gravado) e
# abre o servidor X com o MBindScreen.
XDG_RUNTIME_DIR="/run/user/$(id -u)"
export XDG_RUNTIME_DIR
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
mkdir -p "$HOME/.config/mbind-screen"
echo mbind > "$HOME/.config/mbind-screen/boot-screen"
exec /usr/bin/xinit "$SCRIPT_DIR/MBindScreen-session.sh"
