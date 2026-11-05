#!/bin/bash
# Cliente X: nao deixa o ecra apagar sozinho e corre a aplicacao.
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
xset s off -dpms s noblank 2>/dev/null
# shellcheck disable=SC2086
exec "$MBS_PYTHON" "$SCRIPT_DIR/../MBindScreen/MBindScreen.py" --fullscreen $MBS_ARGS
