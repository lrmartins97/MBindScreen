#!/bin/bash
# Corre uma vez no arranque da maquina. Le' o ultimo ecra escolhido e arranca-o.
# Sem escolha gravada, ou com o MBindScreen por instalar, fica o KlipperScreen.
CHOICE="$(cat "$1/.config/mbind-screen/boot-screen" 2>/dev/null)"
if [ "$CHOICE" = "mbind" ] && [ -f /etc/systemd/system/MBindScreen.service ]; then
    exec systemctl --no-block start MBindScreen.service
fi
exec systemctl --no-block start KlipperScreen.service
