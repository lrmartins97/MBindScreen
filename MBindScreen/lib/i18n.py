"""Interface language. The source text is Portuguese and is also the key.

The choice lives in a file, read once when this module loads: changing it restarts
the screen, so even module constants come out in the new language. What comes from
Klipper (macro messages, material names) stays as the machine sends it.
"""
from __future__ import annotations

import pathlib

PORTUGUESE, ENGLISH = "pt", "en"
LANGUAGES = {PORTUGUESE: "Português", ENGLISH: "English"}
LANGUAGE_FILE = pathlib.Path.home() / ".config" / "mbind-screen" / "language"

ENGLISH_TEXT = {
    # States and steps
    "Pronta": "Ready",
    "A imprimir": "Printing",
    "Em pausa": "Paused",
    "Impressão concluída": "Print finished",
    "Impressão cancelada": "Print cancelled",
    "Erro na impressão": "Print error",
    "A arrancar": "Starting",
    "Paragem de emergência": "Emergency stop",
    "Erro no Klipper": "Klipper error",
    "Klipper desligado": "Klipper disconnected",
    "Interior": "Chamber",
    "Nozzle Align": "Nozzle Align",
    "Seringa T0": "Syringe T0",
    "Seringa T1": "Syringe T1",
    "Preparar": "Prepare",
    "Aquecer": "Heat",
    "Calibrar": "Calibrate",
    "Limpar": "Clean",
    "Purga": "Purge",
    # Connection
    "Modo de experiência: comando não enviado": "Trial mode: command not sent",
    "Modo de experiência: os comandos não chegam à máquina":
        "Trial mode: commands do not reach the machine",
    "Ligação ao Moonraker perdida": "Connection to Moonraker lost",
    "Sem ligação ao Moonraker": "No connection to Moonraker",
    "A ligar ao Moonraker…": "Connecting to Moonraker…",
    "A aguardar pelo serviço da impressora.": "Waiting for the printer service.",
    "Reiniciar firmware": "Restart firmware",
    "Reiniciar Klipper": "Restart Klipper",
    # Common buttons
    "Seguinte": "Next",
    "Cancelar": "Cancel",
    "Parar": "Stop",
    "Voltar": "Back",
    "Ligar": "Connect",
    "Desligar": "Turn off",
    "Ligar Wi-Fi": "Turn Wi-Fi on",
    "Desligar Wi-Fi": "Turn Wi-Fi off",
    "Confirmar": "Confirm",
    "Gravar": "Save",
    "Atualizar": "Update",
    "Verificar": "Check",
    "Mudar": "Switch",
    "Reiniciar": "Restart",
    "Aceitar": "Accept",
    "Concluir": "Finish",
    "Procurar": "Search",
    "Falhou": "Failed",
    "Concluído": "Done",
    "espaço": "space",
    # Manual X/Y
    "A cabeça está a deslocar-se. Aguarda.": "The head is moving. Please wait.",
    "Calibração X/Y": "X/Y calibration",
    "Calibração Z": "Z calibration",
    "Calibração X/Y manual · T{}": "Manual X/Y calibration · T{}",
    "Cancelar a calibração? O passo atual não é gravado.":
        "Cancel the calibration? The current step is not saved.",
    "Cancelar calibração": "Cancel calibration",
    "A cancelar a calibração": "Cancelling the calibration",
    "Paragem de emergência? Pára tudo de imediato.":
        "Emergency stop? Everything stops immediately.",
    "Paragem de emergência? Pára tudo de imediato. Depois é preciso reiniciar o firmware.":
        "Emergency stop? Everything stops immediately. The firmware must then be restarted.",
    "Passo (mm)": "Step (mm)",
    # Calibration
    "Calibração": "Calibration",
    "Gravar e reiniciar": "Save and restart",
    "Alinhar os bicos": "Align the nozzles",
    "Calibração entre o T0 e o T1, a mais importante.":
        "Calibration between T0 and T1, the most important one.",
    "Altura e prato": "Height and plate",
    "Altura dos bicos, nivelamento e placas.": "Nozzle height, levelling and well plates.",
    "Câmara e diagnóstico": "Camera and diagnostics",
    "Foco da câmara e medição de vibrações.": "Camera focus and vibration measurement.",
    "Calibração entre ferramentas": "Tool-to-tool calibration",
    "Z e X/Y do T1 em relação ao T0 (CALIBRATE_IDEX).":
        "Z and X/Y of T1 relative to T0 (CALIBRATE_IDEX).",
    "Só X/Y entre bicos": "X/Y between nozzles only",
    "Exige o Z calibrado.": "Needs Z to be calibrated.",
    "Só Z entre bicos": "Z between nozzles only",
    "Depois é preciso refazer o X/Y.": "X/Y must be redone afterwards.",
    "Estado da calibração": "Calibration status",
    "Offsets, estado e datas.": "Offsets, status and dates.",
    "Altura do Z do T0": "T0 Z height",
    "Teste do papel (CALIBRAR_Z).": "Paper test (CALIBRAR_Z).",
    "Nivelar o prato": "Level the plate",
    "Ajuste dos 3 parafusos.": "Adjust the 3 screws.",
    "Ajuste fino do T1": "T1 fine adjustment",
    "Soma à altura calibrada do T1.": "Added to the calibrated height of T1.",
    "Altura de uma placa": "Well plate height",
    "Fundo de uma placa ou caixa de Petri.": "Bottom of a well plate or Petri dish.",
    "Foco da câmara": "Camera focus",
    "Depois de mexer na lente.": "After touching the lens.",
    "Medir vibrações do T0": "Measure T0 vibrations",
    "Medir vibrações do T1": "Measure T1 vibrations",
    "Medir vibrações do T{}": "Measure T{} vibrations",
    "Só mede: não muda a configuração.": "Measures only: the configuration is not changed.",
    "Automática (câmara e switch)": "Automatic (camera and switch)",
    "Z pelo papel": "Z by paper",
    "X/Y pela mira": "X/Y by crosshair",
    "Automático": "Automatic",
    "Ajuste do T1 (mm)": "T1 adjustment (mm)",
    "Afastar do prato (+)": "Away from the plate (+)",
    "Aproximar do prato (−)": "Closer to the plate (−)",
    "Gravar os valores novos? O Klipper reinicia.": "Save the new values? Klipper restarts.",
    "Não gravar: há valores do input shaper pendentes, e com estes o Klipper não arranca "
    "nesta máquina. Reinicia o Klipper para os descartar.":
        "Do not save: input shaper values are pending, and Klipper does not start on this "
        "machine with them. Restart Klipper to discard them.",
    "Valores por gravar: {}": "Values to save: {}",
    # Cameras
    "Câmaras": "Cameras",
    "Todas": "All",
    "A procurar câmaras...": "Looking for cameras...",
    "Sem câmaras configuradas": "No cameras configured",
    "Não foi possível obter a lista de câmaras": "Could not get the list of cameras",
    "Sem imagem da câmara": "No camera image",
    # Control
    "Mover": "Move",
    "Cabeça ativa": "Active head",
    "Câmara": "Chamber",
    "Prato\n▲": "Plate\n▲",
    "Prato\n▼": "Plate\n▼",
    "Distância (mm)": "Distance (mm)",
    "Desligar motores": "Motors off",
    "Luz": "Light",
    "Ventoinha": "Fan",
    "Fazer home a todos os eixos? Sem o home do Z feito, o prato desce 8 mm em cada home.":
        "Home all axes? Without Z homed, the plate drops 8 mm on every home.",
    "Ligar os LED UV a {}%? Não olhar diretamente para a luz.":
        "Turn the UV LEDs on at {}%? Do not look directly at the light.",
    "Ligar UV": "Turn UV on",
    "Limite do eixo {} atingido.": "{} axis limit reached.",
    "Sem\nhome": "Not\nhomed",
    # Files and home page
    "Ficheiros": "Files",
    "Pasta acima": "Parent folder",
    "Estimativa {}": "Estimate {}",
    "\nEstimativa: {}": "\nEstimate: {}",
    "Imprimir {}?{}": "Print {}?{}",
    "Imprimir": "Print",
    "Não foi possível iniciar: {}": "Could not start: {}",
    "Não foi possível ler os ficheiros.": "Could not read the files.",
    "Pasta vazia.": "Empty folder.",
    "Ativa": "Active",
    "alvo {:.0f} °C": "target {:.0f} °C",
    "Impressão": "Print",
    "Sem home feito": "Not homed",
    "Home feito": "Homed",
    "desligada": "off",
    # Network
    "Rede": "Network",
    "No modo de experiência só leitura não se muda a rede.":
        "The network cannot be changed in the read-only trial mode.",
    "Ativar o hotspot? O Wi-Fi deixa a rede atual, e quem estiver ligado pelo Mainsail ou por "
    "SSH perde a ligação.":
        "Turn the hotspot on? Wi-Fi leaves the current network, and anyone connected through "
        "Mainsail or SSH loses the connection.",
    "Desativar o hotspot? Quem estiver ligado a ele perde a ligação.":
        "Turn the hotspot off? Anyone connected to it loses the connection.",
    "Sem placa de rede": "No network adapter",
    "Ligada · {}": "Connected · {}",
    "Sem cabo": "No cable",
    "Cabo ligado, sem rede": "Cable connected, no network",
    "Sem Wi-Fi": "No Wi-Fi",
    "Em uso pelo hotspot": "In use by the hotspot",
    "Ligado · {}": "Connected · {}",
    "Desligado": "Off",
    "Sem ligação": "Not connected",
    "A ler...": "Reading...",
    "Desligar a Ethernet?": "Disconnect Ethernet?",
    "Ligar a Ethernet?": "Connect Ethernet?",
    "Não foi possível mudar a Ethernet.": "Could not change Ethernet.",
    "Ativar": "Turn on",
    "Desativar": "Turn off",
    "Mudar nome e palavra-passe": "Change name and password",
    "Nome do hotspot": "Hotspot name",
    "Palavra-passe de {}": "Password for {}",
    "A aguardar...": "Please wait...",
    "Ativo: {} · {}": "On: {} · {}",
    "Ativo: {}": "On: {}",
    "Ativo · {}": "On · {}",
    "Desligado: {}": "Off: {}",
    "Por configurar": "Not set up",
    "Não foi possível ativar o hotspot.": "Could not turn the hotspot on.",
    "Não foi possível desativar o hotspot.": "Could not turn the hotspot off.",
    "Desligar o Wi-Fi? Sem cabo de rede, a máquina fica sem Mainsail nem SSH até o voltares a "
    "ligar neste ecrã.":
        "Turn Wi-Fi off? Without a network cable, the machine has no Mainsail or SSH until you "
        "turn it back on from this screen.",
    "Ligar a {ssid}? A máquina pode mudar de endereço, e quem estiver ligado pelo Mainsail ou "
    "por SSH perde a ligação.":
        "Connect to {ssid}? The machine may change address, and anyone connected through "
        "Mainsail or SSH loses the connection.",
    "Sinal {}%": "Signal {}%",
    "Protegida": "Secured",
    "Aberta": "Open",
    "Ligada": "Connected",
    "Guardada": "Saved",
    "A procurar redes...": "Searching for networks...",
    "Wi-Fi não disponível": "Wi-Fi not available",
    "Wi-Fi desligado": "Wi-Fi off",
    "A ligar a {}...": "Connecting to {}...",
    "Ligada a {} · {}": "Connected to {} · {}",
    "Sem ligação Wi-Fi": "No Wi-Fi connection",
    "Não foi possível ligar a {}. Confirma a palavra-passe e o sinal.":
        "Could not connect to {}. Check the password and the signal.",
    # Print
    "Pausa": "Pause",
    "Retomar": "Resume",
    "Cancelar impressão": "Cancel print",
    "Cancelar a impressão? Não pode ser retomada.": "Cancel the print? It cannot be resumed.",
    "A preparar": "Preparing",
    "Ajuste de Z: {:+.3f} mm": "Z adjustment: {:+.3f} mm",
    "Temperatura T{}": "Temperature T{}",
    "Limite do ajuste de Z atingido (±{:g} mm)": "Z adjustment limit reached (±{:g} mm)",
    "Sem impressão": "No print",
    "Camada": "Layer",
    "Decorrido": "Elapsed",
    "Restante": "Remaining",
    # Settings
    "Definições": "Settings",
    "Idioma": "Language",
    "Modo de programador": "Developer mode",
    "Computador": "Computer",
    "Placa principal": "Main board",
    "Placa da cabeça T{}": "Head board T{}",
    "Acesso remoto.": "Remote access.",
    "Tailscale não disponível": "Tailscale not available",
    "Por autenticar": "Not logged in",
    "Desligar o Tailscale? Perde-se o acesso remoto a esta máquina.":
        "Turn Tailscale off? Remote access to this machine is lost.",
    "Não foi possível. Sem password, é preciso autorizar uma vez por SSH: "
    "sudo tailscale set --operator=$USER":
        "Could not do it. To work without a password, authorise it once over SSH: "
        "sudo tailscale set --operator=$USER",
    "Código de programador": "Developer code",
    "Código para mudar de ecrã, atualizar e reiniciar.":
        "Code to switch screens, update and restart.",
    "Ativo. Toca para sair.": "On. Tap to leave.",
    "Código errado.": "Wrong code.",
    "Português ou inglês.": "Portuguese or English.",
    "Mensagens": "Messages",
    "Sistema": "System",
    "Atualizações": "Updates",
    "A verificar…": "Checking…",
    "Atualizar o MBind UI? O ecrã reinicia no fim.":
        "Update MBind UI? The screen restarts at the end.",
    "Ecrã": "Screen",
    "Mudar para o KlipperScreen? O ecrã fica preto alguns segundos.":
        "Switch to KlipperScreen? The screen goes black for a few seconds.",
    "Mudar para o KlipperScreen?": "Switch to KlipperScreen?",
    "O KlipperScreen continua instalado. Podes mudar a qualquer momento, mesmo durante uma "
    "impressão: a impressão não é afetada. A máquina arranca com o último ecrã escolhido.":
        "KlipperScreen is still installed. You can switch at any time, even during a print: "
        "the print is not affected. The machine starts with the last screen chosen.",
    "Mudar para o KlipperScreen": "Switch to KlipperScreen",
    "Mudar para o KlipperScreen.": "Switch to KlipperScreen.",
    "Não foi possível mudar: {}": "Could not switch: {}",
    "Limpar avisos": "Clear warnings",
    "Nome": "Name",
    "Não é possível atualizar durante uma impressão.": "Cannot update during a print.",
    "Reiniciar o Klipper": "Restart Klipper",
    "Reiniciar o firmware": "Restart the firmware",
    "Reiniciar o computador": "Restart the computer",
    "Desligar o computador": "Shut down the computer",
    "Avisos e consola do Klipper.": "Warnings and Klipper console.",
    "Ethernet, Wi-Fi e hotspot.": "Ethernet, Wi-Fi and hotspot.",
    "Versões e endereço de rede.": "Versions and network address.",
    "Estado do que o Moonraker atualiza.": "Status of what Moonraker updates.",
    "Klipper, firmware e computador.": "Klipper, firmware and computer.",
    "Atualização disponível": "Update available",
    "Atualizado": "Up to date",
    # Syringes
    "Limpar o bico do T{}? A cabeça desloca-se para as estações de limpeza (faz home se for "
    "preciso).":
        "Clean the T{} nozzle? The head moves to the cleaning stations (homing if needed).",
    "O êmbolo empurra {} a {}/s (seringa de {:g} mm)":
        "The plunger pushes {} at {}/s ({:g} mm syringe)",
    "Recuar": "Retract",
    "Avançar": "Extrude",
    "Limpar bico": "Clean nozzle",
    "Limpar bico T{}": "Clean nozzle T{}",
    "Material da seringa T{}": "Material of syringe T{}",
    "Seringa T{}": "Syringe T{}",
    "Toca na temperatura para a mudar": "Tap the temperature to change it",
    "Sem material": "No material",
    "Material {}": "Material {}",
    "Quanto o êmbolo anda (mm)": "Plunger travel (mm)",
    "Velocidade do êmbolo (mm/s)": "Plunger speed (mm/s)",
    # Adjustment screens
    "Sobe o prato até o bico prender ligeiramente uma folha de papel. Valores negativos "
    "aproximam o prato do bico.":
        "Raise the plate until the nozzle lightly grips a sheet of paper. Negative values "
        "bring the plate closer to the nozzle.",
    "Roda o parafuso até o bico prender a folha de papel. Se mexeste nele, carrega em Ajustei "
    "o parafuso; se já estava bem, em Aceitar.":
        "Turn the screw until the nozzle grips the paper. If you turned it, press Screw "
        "adjusted; if it was already right, press Accept.",
    " · {} aceites": " · {} accepted",
    "{} ({:g} a {:g})": "{} ({:g} to {:g})",
    "Ajustei o parafuso": "Screw adjusted",
    "Teste do papel": "Paper test",
    "Ajuste dos parafusos do prato": "Plate screw adjustment",
    "Parafuso {}": "Screw {}",
    " · ajuste fino": " · fine adjustment",
    # Routines
    "A começar…": "Starting…",
    "Sem mensagens da máquina.": "No messages from the machine.",
}


def _read_language() -> str:
    try:
        code = LANGUAGE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return PORTUGUESE
    return code if code in LANGUAGES else PORTUGUESE


_language = _read_language()


def language() -> str:
    return _language


def save_language(code: str) -> None:
    """Takes effect when the screen restarts."""
    LANGUAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LANGUAGE_FILE.write_text(code + "\n", encoding="utf-8")


def tr(text: str, *values: object) -> str:
    """``text`` in the chosen language, with ``values`` in its {} fields, if any."""
    translated = ENGLISH_TEXT.get(text, text) if _language == ENGLISH else text
    return translated.format(*values) if values else translated
