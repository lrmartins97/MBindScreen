#!/bin/bash
# Deixa a maquina como estava: so' KlipperScreen, a arrancar sozinho.
# O codigo em ~/MBindScreen e o ambiente Python ficam: apagam-se a mao.
set -uo pipefail
ASVC="$HOME/printer_data/moonraker.asvc"
MOONRAKER_CONF="$HOME/printer_data/config/moonraker.conf"
UNIT_DIR=/etc/systemd/system

sudo systemctl disable mbind-screen-boot.service
sudo systemctl stop MBindScreen.service
sudo rm -f "$UNIT_DIR/MBindScreen.service" "$UNIT_DIR/mbind-screen-boot.service"
sudo systemctl daemon-reload
sudo systemctl enable --now KlipperScreen.service
sed -i '/^MBindScreen$/d' "$ASVC"
rm -rf "$HOME/.config/mbind-screen"
if grep -q "update_manager MBindScreen" "$MOONRAKER_CONF"; then
    echo "Tira o bloco [update_manager MBindScreen] do moonraker.conf."
fi
sudo systemctl restart moonraker
echo "MBindScreen removido. KlipperScreen ativo."
