# Integração com o m-bind-config

O `install.sh` acrescenta o bloco do Update Manager ao `moonraker.conf` da máquina,
para se poder experimentar já. Como esse ficheiro está no git, essa alteração aparece
no `git status` da máquina e pode entrar em conflito num `git pull`. Para as máquinas
ficarem iguais, estas alterações devem passar para o repositório `m-bind-config`.

## moonraker.conf

```ini
[update_manager MBindScreen]
type: git_repo
path: ~/MBindScreen
origin: https://github.com/lrmartins97/MBindScreen.git
primary_branch: main
virtualenv: ~/.MBindScreen-env
requirements: scripts/requirements.txt
system_dependencies: scripts/system-dependencies.json
is_system_service: False
```

`is_system_service: False` é intencional: ver "Atualizar" no README.

Numa máquina que já tenha o bloco acrescentado pelo instalador, antes do `git pull`:
`git checkout moonraker.conf`.

## KlipperScreen.conf: botão para saltar para o MBindScreen

Acrescentar **antes** da linha `#~# --- Do not edit below this line`:

```ini
[menu __main more mbindscreen]
name: MBindScreen
icon: settings
method: machine.services.start
params: {"service": "MBindScreen"}
confirm: Mudar para o ecrã MBindScreen?
```

## instalar.sh

Acrescentar a instalação ao lado dos outros programas, para uma máquina nova:

```bash
git clone https://github.com/lrmartins97/MBindScreen.git ~/MBindScreen
bash ~/MBindScreen/scripts/install.sh
```

## O que não precisa de mudar

- Macros: o ecrã usa as que já existem. O teste `test_gcode_commands.py` avisa se
  alguma for renomeada.
- `[usb_import] screen_service: KlipperScreen`: o vigilante só reinicia o serviço se ele
  estiver a correr sem ligação; nunca arranca um serviço parado. Com o MBindScreen ativo
  não faz nada.
- `moonraker.asvc`: fica fora do git, e o instalador trata dele.
