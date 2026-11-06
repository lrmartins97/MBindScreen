# Partilhado por install.sh, experimentar.sh e uninstall.sh. Nao se corre sozinho.
PACKAGES_RECORD="$HOME/.config/mbind-screen/pacotes-instalados"

fail() { printf '\033[0;31m%s\033[0m\n' "$1"; exit 1; }

# idle_timeout "Printing" apanha tambem macros e calibracoes, fora de uma impressao.
# Sem resposta do Moonraker nao ha como saber, e deixa continuar.
refuse_if_busy() {
    local state
    state="$(curl -fsS \
        'http://localhost:7125/printer/objects/query?print_stats=state&idle_timeout=state' \
        2>/dev/null || true)"
    case "$state" in
        *'"printing"'*|*'"paused"'*|*'"Printing"'*)
            fail "A maquina esta a trabalhar. Tenta outra vez quando estiver parada." ;;
    esac
}

# Entrada do Update Manager do Moonraker. O nome tem de estar em minusculas. O Moonraker
# nao reinicia o servico, de proposito: a aplicacao sai sozinha quando acaba a atualizacao.
add_update_manager() {
    local conf="$HOME/printer_data/config/moonraker.conf" app="$1" env="$2"
    grep -q "^\[update_manager mbind-ui\]" "$conf" && return 0
    cat >> "$conf" <<EOF

[update_manager mbind-ui]
type: git_repo
path: $app
origin: $(git -C "$app" remote get-url origin)
primary_branch: $(git -C "$app" rev-parse --abbrev-ref HEAD)
virtualenv: $env
requirements: scripts/requirements.txt
system_dependencies: scripts/system-dependencies.json
is_system_service: False
EOF
}

installed_packages() {
    dpkg-query -W -f='${db:Status-Abbrev} ${Package}\n' \
        | awk '$1 == "ii" { print $2 }' | LC_ALL=C sort -u
}

# So' instala o que falta e guarda o que apareceu de novo, com as dependencias: e' essa
# lista que o uninstall.sh remove. O que ja existia nao e' atualizado nem marcado, e os
# .deb descarregados nao ficam na cache.
install_missing_packages() {
    local wanted before missing status=0
    wanted="$(python3 -c "import json,sys; \
print('\n'.join(json.load(open(sys.argv[1]))['debian']))" "$1" | LC_ALL=C sort -u)"
    before="$(installed_packages)"
    missing="$(LC_ALL=C comm -23 <(echo "$wanted") <(echo "$before"))"
    if [ -z "$missing" ]; then
        echo "Nao falta nenhum pacote do sistema."
        return 0
    fi
    # shellcheck disable=SC2086
    sudo apt-get install -y --no-upgrade --no-install-recommends \
        -o APT::Keep-Downloaded-Packages=false $missing || status=$?
    mkdir -p "$(dirname "$PACKAGES_RECORD")"
    LC_ALL=C comm -13 <(echo "$before") <(installed_packages) >> "$PACKAGES_RECORD"
    LC_ALL=C sort -u -o "$PACKAGES_RECORD" "$PACKAGES_RECORD"
    return "$status"
}
