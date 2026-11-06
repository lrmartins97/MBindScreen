# CLAUDE.md: MBindScreen

Contexto para o Claude Code continuar o projeto em qualquer PC. O README explica o que
é e como se organiza; aqui está o que não se vê no código e o que evita estragos.

## O projeto

Ecrã tátil da M-BIND (IDEX de seringas da Blocks, para farmácia e bioimpressão), em
PyQt6, a falar com o Klipper pelo Moonraker. Nasceu porque o MyScreen (RF50) é apelativo
mas desorganizado: o aspeto vem daí, a organização vem do BlocksScreen
(`BlocksTechnology/BlocksScreen`), que é fácil de depurar. É código novo, não um fork.

- Repositório público, branch `main`.
- A configuração das máquinas está num repositório privado, `m-bind-config`, com o seu
  próprio `CLAUDE.md`: ler antes de tocar em macros. Não se altera sem pedido.
- Ecrã de 800x480, com toque USB.

## Decisões do utilizador

- **O KlipperScreen não se remove** e tem de dar para voltar a ele a qualquer momento.
- **O projeto ainda é embrionário.** Na máquina usa-se `scripts/experimentar.sh`, que
  não deixa nada no arranque. `install.sh` só quando o utilizador disser que está maduro.
- **Tudo tem de sair com `scripts/uninstall.sh`**, e a máquina tem de ficar como estava.
  O que for escrito fora do repositório, novo pacote incluído, tem de ser desfeito lá.
- **Cores claras** (é uma máquina de farmácia): branco com o azul Blocks `#00a8ff`.
  Nunca voltar ao tema escuro e laranja do MyScreen. O azul dá 2,6:1 nos ícones, abaixo
  do recomendado: foi escolha do utilizador, e `test_theme.py` regista-o.
- Texto da interface, documentação e commits em português. O código em inglês.
- **Idiomas:** todo o texto novo da interface passa por `tr()` e tem tradução em
  `lib/i18n.py`; o `test_i18n.py` falha se faltar. Não usar `tr()` em textos comparados com
  mensagens do Klipper (`PREPARE_STAGES`, `PRINTING_MESSAGE`).
- Página de rede organizada como no BlocksScreen: Ethernet, Wi-Fi e hotspot.

## Dados confidenciais

Este repositório é público. **Nada das máquinas reais entra aqui**, em nenhum ficheiro,
teste, commit ou captura: IPs, hostnames, nomes de redes Wi-Fi, palavras-passe, números
de série, posições e valores calibrados, nem dados pessoais. Os testes e o simulador usam
valores inventados (endereços `192.0.2.x`). O que for de uma máquina fica na memória
local do Claude ou no `m-bind-config`. Antes de publicar, procurar estes dados no diff.

## Como trabalhar

- **Só fazer commit e push quando o utilizador disser "publica".**
- **Num PC novo, antes do primeiro commit**, configurar o `user.email` deste repositório
  com o endereço noreply do GitHub, para o email pessoal não ir para o histórico. A
  configuração local do git não viaja com o clone.
- Confirmar qual é a máquina antes de agir: as máquinas têm todas o mesmo hostname, e o
  IP muda conforme a rede.
- Antes de qualquer ação na máquina, ver se está parada:
  `/printer/objects/query?print_stats=state&idle_timeout=state`.

## Testar no PC

```
pip install -r scripts/requirements-dev.txt
pip install PyQt6==6.10.0 PyQt6-Qt6==6.10.0    # a mesma versão da máquina
QT_QPA_PLATFORM=offscreen python -m pytest -q
python MBindScreen/MBindScreen.py --simulate
```

- `test_gcode_commands.py` compara com os `.cfg` reais: precisa do `m-bind-config` ao
  lado desta pasta, ou de `MBIND_CONFIG` a apontar para ele.
- `test_uninstall.py` corre os scripts em bash com comandos falsos (no Windows, o Git
  Bash). Prova a lógica, não o `apt` nem o `systemctl` reais.
- Com uma máquina na rede, ver dados reais sem risco:
  `python MBindScreen/MBindScreen.py --host <IP> --read-only`.

## Modo de programador

Definições > Modo de programador pede um código e mostra Ecrã, Atualizações e Reiniciar.
O repositório guarda só o SHA-256 do código; cada máquina pode ter o seu em
`[screen] developer_code` no `MBindScreen.cfg`. Fecha sozinho quando o ecrã reinicia.
O código não está escrito em nenhum ficheiro deste repositório.

## Testar na máquina

```
ssh <utilizador>@<IP>
bash ~/MBindScreen/scripts/experimentar.sh ver 30     # sem enviar comandos
bash ~/MBindScreen/scripts/experimentar.sh usar 30    # os botões atuam mesmo
bash ~/MBindScreen/scripts/experimentar.sh parar      # volta ao KlipperScreen
```

Reiniciar a máquina volta sempre ao KlipperScreen. Para atualizar, a ordem importa:
**`parar`, depois `git pull`, depois `ver` ou `usar`.** O `pull` não reinicia o programa
em execução, e `ver`/`usar` com o ecrã ligado não fazem nada.

- Depois de reiniciar a máquina, o `sudo` pede password: só o utilizador pode correr
  estes comandos na sessão dele. O Claude consegue ler por SSH, se tiver chave.
- Ver o que está no ecrã, por SSH (grava `/tmp/ecra.png`):
  `DISPLAY=:0 QT_QPA_PLATFORM=xcb ~/.MBindScreen-env/bin/python` com
  `QGuiApplication` e `primaryScreen().grabWindow(0).save(...)`.
- Log: `~/printer_data/logs/MBindScreen.log`, que tem cada G-code enviado.
  Ecrã preto: `journalctl -u MBindScreen-try -n 50 --no-pager`.
- `KlipperScreen failed` em `experimentar.sh estado` é normal enquanto corre a
  experiência: é como ele sai ao ser parado.

## Armadilhas já encontradas

- **Testes que carregam em botões por código não provam que estão visíveis.** Uma janela
  com 1 px de altura bloqueou o ecrã e passou nos testes. `test_dialogs.py` verifica
  agora a geometria; fazer o mesmo em janelas novas.
- **Cada pixel conta:** a janela não pode passar dos 480 px, com ou sem a faixa do modo
  de experiência (24 px), senão corta o fundo do ecrã, incluindo a emergência.
  `test_every_page_fits_the_screen` garante-o.
- **Sem cabo de rede, o Wi-Fi é a única ligação:** testar hotspot, desligar o Wi-Fi ou
  mudar de rede corta o SSH, por isso faz-se à frente da máquina.
- **Passwords nunca vão para o log.** Em `wifi.py` e `wifiPage.py` regista-se só o nome.
- **No PowerShell, `~` sozinho é a pasta pessoal:** `git clone ... ~/x` cria uma pasta
  chamada `~`, e `rm ~` apagaria a pasta pessoal.
- **Moonraker:** não corre `install_script`; só autoriza serviços carregados quando
  arrancou; depois de atualizar reinicia os serviços, daí o `is_system_service: False`.
- **Estado do Klipper:** chega a cada 250 ms e pode vir depois da resposta a um comando,
  daí o `SETTLE_MS` do `Runner`.
- **Câmaras:** a lista vem do Moonraker, com a inversão definida no Mainsail. A imagem da
  calibração tem de ficar igual à do Mainsail (`calibration_mirror`), senão o jog parece
  invertido. A vista do kTAMV mostra uma imagem de teste até o servidor receber
  configuração.
- **Windows:** os testes escrevem ficheiros para bash com `write_bytes`, porque
  `write_text` põe CRLF. Heredocs grandes no Bash podem falhar: usar a ferramenta Write.

## Estado em 2026-11-06

Confirmado na máquina: arranque com X, toque, as 4 câmaras, o menu de câmaras, a volta
ao KlipperScreen (por tempo, por comando e a reiniciar), e a calibração X/Y manual
completa e gravada.

Por confirmar em `3c79065`: foto e cor no ecrã real, setas de X e Y nas duas páginas,
seringas (toque e manter premido), teclado numérico, página Rede, troca de T0/T1, êmbolo
e impressão de teste. Hotspot, desligar o Wi-Fi e mudar de rede nunca correram de verdade.
O resto está em `docs/por-fazer.md`.

Decisões pendentes do utilizador:
1. **Botão de emergência por cima das janelas.** Com uma janela aberta são precisos dois
   toques. Recomendado antes de mais testes com movimento.
2. **Limpeza da primeira instalação.** Foi feita com uma versão sem registo de pacotes.
   O que entrou está no `/var/log/apt/history.log` da máquina e tem de ir para
   `~/.config/mbind-screen/pacotes-instalados`, senão o `uninstall.sh` não o remove.
   Essa versão deixou também ficheiros novos em `~/.cache/pip`, entre outros mais antigos
   que não são nossos.
3. **Hotspot:** continuar com `nmcli` direto, ou passar às macros `HOTSPOT_*` se o
   `klipper-hotspot` for instalado.
4. **Alterar o `m-bind-config`:** botão no KlipperScreen e bloco do Moonraker, só preciso
   para o `install.sh` (`docs/integracao-m-bind-config.md`).
