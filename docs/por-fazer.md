# Por fazer

## Confirmar na máquina (primeira instalação)

Nada disto foi corrido num Raspberry Pi. Foi escrito a partir do código do Moonraker e
do KlipperScreen, e dos testes no PC. Os scripts e os serviços systemd nunca correram.
Primeiro a experiência (`docs/experimentar-na-maquina.md`); os pontos sobre o arranque
e o Moonraker só se aplicam ao `install.sh`.

1. `install.sh` corre até ao fim e `ecra.sh mbind` mostra o ecrã (X no Pi 5).
2. O toque funciona e está alinhado.
3. Ecrã BTT HDMI5 (800x480, toque por USB): ver se a imagem preenche o ecrã.
4. Saltar nos dois sentidos, com a máquina ligada há pouco e **depois de um reinício**
   com cada ecrã escolhido.
5. `bash ecra.sh estado` e o `available_services` em `/machine/system_info` mostram os
   dois serviços depois de um reinício.
6. Fazer falhar o MBindScreen quatro vezes e confirmar que entra o KlipperScreen.
7. Atualizar pelo Moonraker com cada um dos ecrãs ativo.
8. Nomes reais do `dual_carriage` (`carriage_0`, `carriage_1`) e do `bed_screws` na
   versão do Klipper instalada.
9. Teste do papel e parafusos do início ao fim na máquina.
10. Calibração X/Y manual: a imagem chega por `/webcam2/snapshot` (nginx) e a página
    abre com a imagem nítida. Confirmar também o sentido do jog em relação à imagem: a
    câmara olha para cima, por isso X ou Y podem parecer invertidos no ecrã.
11. O Klipper manda a mesma mensagem `M117` que o ecrã espera em cada etapa do
    `PRINT_START` (o teste compara com os ficheiros `.cfg`).

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
