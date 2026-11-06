# MBindScreen

Ecrã tátil da M-BIND (IDEX de seringas). Tema claro em branco e azul Blocks, organização
do BlocksScreen, e feito para esta máquina: duas seringas, sem filamento, sem cama
aquecida. Fala com o Klipper pelo Moonraker e **corre ao lado do KlipperScreen**: dá
para saltar entre os dois a qualquer momento.

## Experimentar no PC (sem impressora)

```
pip install -r scripts/requirements-dev.txt
python MBindScreen/MBindScreen.py --simulate
```

Com uma impressora real na rede: `python MBindScreen/MBindScreen.py --host <IP>`.
O botão de mover, aquecer e calibrar atua mesmo na máquina.

## Experimentar na impressora

Sem mudar nada de permanente, e com o KlipperScreen a voltar sozinho:
[`docs/experimentar-na-maquina.md`](docs/experimentar-na-maquina.md).

## Instalar na impressora

Só quando estiver maduro: isto muda o arranque da máquina e o `moonraker.conf`.

```
git clone https://github.com/lrmartins97/MBindScreen.git ~/MBindScreen
bash ~/MBindScreen/scripts/install.sh
```

O instalador recusa correr durante uma impressão. No fim o ecrã continua no
KlipperScreen. Ver [`docs/integracao-m-bind-config.md`](docs/integracao-m-bind-config.md)
para o que acrescentar ao repositório da configuração.

## Saltar entre os ecrãs

| A partir de | Como |
|---|---|
| MBindScreen | Definições > Ecrã > Mudar para o KlipperScreen |
| KlipperScreen | Mais > MBindScreen (depois de acrescentar o botão, ver `docs/`) |
| Mainsail | Menu de energia > Serviços: iniciar `MBindScreen` ou `KlipperScreen` |
| SSH | `bash ~/MBindScreen/scripts/ecra.sh mbind`, `klipperscreen` ou `estado` |

- Os dois serviços têm `Conflicts=`: arrancar um pára o outro. O KlipperScreen não é
  alterado nem desinstalado. Não há perigo para uma impressão: os ecrãs são clientes
  do Moonraker e o Klipper continua sozinho.
- A máquina arranca com o último ecrã escolhido
  (`~/.config/mbind-screen/boot-screen`). Sem escolha: KlipperScreen. Exceção: iniciar o
  KlipperScreen pelo Mainsail muda o ecrã só até ao próximo arranque.
- Quatro falhas do MBindScreen em 2 minutos: entra o KlipperScreen sozinho
  (`OnFailure=`). A escolha gravada não muda, por isso o próximo arranque volta a tentar.
- Se o Moonraker atualizar o **KlipperScreen**, reinicia-o e o ecrã salta para ele até
  ao próximo reinício da máquina. Volta-se com o botão.
- Remover tudo, código e pacotes novos incluídos: `bash ~/MBindScreen/scripts/uninstall.sh`.
  Detalhes em [`docs/experimentar-na-maquina.md`](docs/experimentar-na-maquina.md).

## Atualizar

Pelo Mainsail, como o resto (Máquina > Update Manager), ou em Definições >
Atualizações. O Moonraker **não** reinicia este serviço, de propósito: fazê-lo trocaria
o ecrã com o KlipperScreen ativo. A própria aplicação reinicia quando recebe o aviso de
atualização concluída, e só se estiver a correr.

**O repositório tem de ser público** (ou a máquina ter credenciais): o Moonraker faz
`git fetch` sem token, e o `instalar.sh --entrega` apaga as credenciais guardadas.

## Depurar

- **Log:** `~/printer_data/logs/MBindScreen.log`, visível no Mainsail. Tem cada G-code
  enviado, erros do Klipper, mudanças de estado e o traceback de qualquer erro.
  `MBindScreen_fault.log` guarda as falhas nativas do Qt.
- **Mais detalhe:** `--debug` regista todos os pedidos ao Moonraker.
- **Serviço:** `journalctl -u MBindScreen -n 50 --no-pager`.
- Um erro numa página não fecha o ecrã: fica no log e aparece em Definições > Mensagens.

## Organização

```
MBindScreen/
  MBindScreen.py        arranque
  configfile.py         MBindScreen.cfg
  logger.py             log e captura de erros
  lib/
    moonrakerComm.py    websocket JSON-RPC, sem lógica de máquina
    printer.py          estado da máquina; os painéis só leem daqui
    machine.py          o que é da M-BIND: nomes de objetos e contas (sem Qt)
    gcodeCommands.py    TODOS os G-codes que o ecrã envia
    prompts.py          janelas do Klipper (action:prompt_*)
    runner.py           rotinas longas com caixa de estado
    panels/alignPage.py calibração X/Y manual: câmara, mira e jog
    screenSwitch.py     mudar para o KlipperScreen
    simulator.py        M-BIND falsa, com a mesma interface do moonrakerComm
    panels/             um ficheiro por separador
    panels/widgets/     caixas e componentes dos separadores
    utils/              tema, ícones e widgets genéricos
scripts/                instalação, serviços e troca de ecrã
tests/                  testes (pytest)
```

Regras: um painel não fala com o Moonraker para ler estado (usa `Printer`) nem escreve
G-code (usa `gcodeCommands`). Se a configuração da máquina mudar um nome, só mudam
`machine.py` e `gcodeCommands.py`.

## Testes

```
pip install -r scripts/requirements-dev.txt
pytest
```

- `test_ui_flows.py` carrega nos botões reais contra o simulador.
- `test_moonraker_client.py` testa a ligação contra um servidor websocket local.
- `test_gcode_commands.py` confirma que cada macro usada existe no `m-bind-config`
  (procura-o ao lado desta pasta, ou em `MBIND_CONFIG`). Corre-o depois de mudar macros.

## Por fazer

Ver as secções em aberto em [`docs/por-fazer.md`](docs/por-fazer.md).

## Licença

AGPL-3.0, a mesma do BlocksScreen. A disposição dos ecrãs vem do MyScreen e o serviço
systemd segue o do KlipperScreen.
