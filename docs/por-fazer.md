# Por fazer

## Confirmar na máquina (primeira instalação)

A experiência (`docs/experimentar-na-maquina.md`) já correu na M-BIND: o arranque, o
toque, as câmaras e a calibração X/Y manual funcionam. O estado atual está no
`CLAUDE.md`. O `install.sh` e o `uninstall.sh` nunca correram numa máquina.

1. `install.sh` corre até ao fim e `ecra.sh mbind` mostra o ecrã.
2. Saltar nos dois sentidos, com a máquina ligada há pouco e **depois de um reinício**
   com cada ecrã escolhido.
3. `bash ecra.sh estado` e o `available_services` em `/machine/system_info` mostram os
   dois serviços depois de um reinício.
4. Fazer falhar o MBindScreen quatro vezes e confirmar que entra o KlipperScreen.
5. Atualizar pelo Moonraker com cada um dos ecrãs ativo.
6. Nomes reais do `dual_carriage` (`carriage_0`, `carriage_1`) e do `bed_screws` na
   versão do Klipper instalada.
7. Teste do papel e parafusos do início ao fim na máquina.
8. O Klipper manda a mesma mensagem `M117` que o ecrã espera em cada etapa do
   `PRINT_START` (o teste compara com os ficheiros `.cfg`).
9. `uninstall.sh` numa máquina real: deixa tudo como estava.

## Funcionalidades em falta

- **Rede:** ao contrário do BlocksScreen, não há VLAN, IP fixo nem QR code do hotspot.
- **klipper-hotspot:** o ecrã fala com o NetworkManager diretamente. Se esse projeto for
  instalado nas máquinas, passar a usar as macros `HOTSPOT_*`, para haver um só perfil.
- **Reentrar numa calibração manual:** se o ecrã reiniciar a meio, a janela da macro
  perde-se e só resta Cancelar.
- **Tamanho das seringas:** as contas de volume usam o `filament_diameter` do T0 (15 mm).
- **Load / unload do empurrador:** as macros `_SYRINGE_LOAD` e `_SYRINGE_UNLOAD` estão
  "preparadas, sem botão"; o ecrã também ainda não as usa.
- **Macros soltas e consola:** não há lista de macros nem teclado para G-code.
- **Idioma:** só português.
