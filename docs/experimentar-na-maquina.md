# Experimentar na máquina

Sem instalar nada de permanente. Primeiro confirma qual é a máquina: a M-BIND 1 e a 2 têm
as duas o hostname `MBind`.

## O que isto muda na máquina

| | |
|---|---|
| Arranque da máquina, serviço do KlipperScreen | Nada |
| Klipper, macros, `printer_data` | Nada |
| Moonraker e `moonraker.conf` | Nada |
| Fica em disco | `~/MBindScreen`, `~/.MBindScreen-env`, os logs e as bibliotecas de sistema que faltavam (`scripts/system-dependencies.json`). Tudo sai com o desinstalador |
| Fica em `/run` | O serviço temporário: desaparece ao reiniciar |

Quando a experiência acaba, por tempo, por erro ou por comando, o KlipperScreen volta
sozinho. Se tudo correr mal, **desligar e ligar a máquina volta ao KlipperScreen**.

## 1. Preparar (uma vez, por SSH, com a máquina parada)

```
ssh blocks@<IP>
git clone https://github.com/lrmartins97/MBindScreen.git ~/MBindScreen
bash ~/MBindScreen/scripts/experimentar.sh preparar
```

Não precisa de reiniciar nada. O ambiente Python descarrega cerca de 120 MB.

## 2. Só ver (nenhum comando chega à máquina)

```
bash ~/MBindScreen/scripts/experimentar.sh ver
```

Tem uma faixa no topo a dizer "Modo de experiência". Dá para navegar em tudo e carregar
nos botões: os comandos são recusados e aparecem em Definições > Mensagens. Só a paragem
de emergência e a mudança para o KlipperScreen funcionam. Passados 10 minutos volta
sozinho (`ver 30` para 30 minutos, máximo 120).

Confirmar:

- [ ] A imagem preenche o ecrã (800x480) e o texto lê-se bem.
- [ ] O toque acerta onde se carrega, e arrastar faz deslizar as listas.
- [ ] Temperaturas, cabeça ativa, materiais e ficheiros batem certo com o Mainsail.
- [ ] Definições > Ecrã > Mudar para o KlipperScreen volta ao KlipperScreen.

## 3. Usar os botões (atuam mesmo na máquina)

Só depois de o passo 2 estar bem, sem nada a imprimir e com o prato livre:

```
bash ~/MBindScreen/scripts/experimentar.sh usar 30
```

Testar por esta ordem, com a mão perto da paragem de emergência:

- [ ] Aquecer uma seringa a 30 °C e desligar.
- [ ] Home. Confirmar que o X e o Y se movem para o lado certo.
- [ ] Jog em passos de 0.1 e 1 mm. "Prato ▲" tem de subir o prato.
- [ ] Trocar T0 e T1.
- [ ] Mover o êmbolo 0.1 mm a 0.1 mm/s, sem seringa colocada.
- [ ] Calibração X/Y manual: imagem da câmara, sentido do jog e cancelar.
- [ ] Teste do papel e cancelar.
- [ ] Pausa, retomar e cancelar num ficheiro de teste.

## Voltar ao KlipperScreen

Por ordem, da mais simples para a mais drástica:

1. No ecrã: Definições > Ecrã > Mudar para o KlipperScreen.
2. Esperar que acabe o tempo.
3. Por SSH: `bash ~/MBindScreen/scripts/experimentar.sh parar`
4. Reiniciar a máquina: `sudo reboot`, ou desligar e ligar.

## Ver o que correu mal

- Log: `~/printer_data/logs/MBindScreen.log`, também no Mainsail.
- Se o ecrã ficar preto: `journalctl -u MBindScreen-try -n 50 --no-pager`
- `bash ~/MBindScreen/scripts/experimentar.sh estado`

## Atualizar para uma versão nova

```
git -C ~/MBindScreen pull
```

## Remover tudo

```
bash ~/MBindScreen/scripts/uninstall.sh
```

Serve para a experiência e para o `install.sh`, e recusa correr com a máquina a
trabalhar. Sai tudo isto:

- Serviços, autorização no Moonraker e bloco do `moonraker.conf`.
- O código, o ambiente Python, os logs, `~/.config/mbind-screen` e `MBindScreen.cfg`.
- Os pacotes que o MBindScreen instalou, com as dependências. Os que já existiam ficam
  intactos, porque a instalação regista só os novos em
  `~/.config/mbind-screen/pacotes-instalados`.

Se algum pacote novo tiver passado a ser usado por outro programa, não é removido e o
desinstalador mostra o comando para o fazer à mão. Também fica o que estiver no git do
`m-bind-config`, que se muda nesse repositório.

O perfil do hotspot sai. As redes Wi-Fi guardadas ficam, porque são da máquina e não
do ecrã.

Só restam registos do sistema: o histórico do apt e do dpkg e o journal. Um pacote
acrescentado ao `system-dependencies.json` e instalado pelo Update Manager não fica
registado, e tem de se remover à mão.

## Instalar a sério

Só quando estiver maduro: `scripts/install.sh`. Esse sim muda o arranque e o Moonraker,
e é o que permite atualizar pelo Update Manager (ver o README). A experiência não precisa
dele.
