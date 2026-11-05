"""Colours and the application stylesheet.

Light theme for a pharmacy machine: white with the Blocks blue, #00a8ff. Text on it
is dark (INK), because white on this blue is hard to read. tests/test_theme.py checks
the contrast. The pale surfaces are tints of the same blue.
"""

BG = "#ffffff"
NAV = "#e3f5ff"
CARD = "#f2fbff"
BORDER = "#c9ecff"
TEXT = "#1d3a4f"
DIM = "#587387"
INK = "#12324a"  # text on baby blue
BABY_BLUE = "#00a8ff"
BABY_BLUE_PRESSED = "#4dc2ff"
ACCENT = "#00a8ff"
RED = "#c62828"
RED_PRESSED = "#a31f1f"
GREEN = "#1b7f52"
TRACK = "#dcf1fd"
BUTTON = "#e3f6ff"
BUTTON_PRESSED = "#c8ecff"
DISABLED_TEXT = "#5a7080"
DISABLED_BG = "#f1f5f8"
SLIDER_OFF = "#b4c6d2"

QSS = f"""
QWidget {{ background: {BG}; color: {TEXT};
  font-family: 'Roboto', 'DejaVu Sans', 'Segoe UI', sans-serif; font-size: 15px; }}
QLabel {{ background: transparent; }}
#nav {{ background: {NAV}; }}
QToolButton {{ background: transparent; border: none; }}
#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
#cardActive {{ background: {CARD}; border: 2px solid {ACCENT}; border-radius: 14px; }}
#cell {{ background: transparent; }}
#accentBar {{ background: {BABY_BLUE}; border-radius: 1px; }}
#heroTitle {{ font-size: 32px; }}
#heroSub {{ color: {DIM}; font-size: 16px; }}
#cardTitle {{ font-size: 20px; }}
#dim {{ color: {DIM}; font-size: 13px; }}
#value {{ font-size: 18px; }}
#big {{ font-size: 28px; }}
#pageTitle {{ font-size: 24px; }}
#badge {{ background: {RED}; color: white; border-radius: 9px; font-size: 11px; }}
#chip {{ background: {BABY_BLUE}; color: {INK}; border-radius: 8px; padding: 1px 8px;
  font-size: 12px; font-weight: 600; }}
#scrim {{ background: rgba(29, 58, 79, 120); }}
#popup {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 16px; }}
#display {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
  font-size: 32px; padding: 8px 16px; }}
#sleep {{ background: black; }}
#trial {{ background: {BABY_BLUE}; color: {INK}; padding: 3px 12px; font-weight: 600; }}
QProgressBar {{ background: {TRACK}; border: none; border-radius: 3px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QPushButton {{ background: {BUTTON}; border: none; border-radius: 12px; font-size: 17px;
  padding: 8px; }}
QPushButton:pressed {{ background: {BUTTON_PRESSED}; }}
QPushButton:disabled {{ color: {DISABLED_TEXT}; background: {DISABLED_BG}; }}
QPushButton#back {{ font-size: 32px; background: transparent; }}
QPushButton#accent {{ background: {BABY_BLUE}; color: {INK}; font-weight: 600; }}
QPushButton#accent:pressed {{ background: {BABY_BLUE_PRESSED}; }}
QPushButton#accent:disabled {{ background: {DISABLED_BG}; color: {DISABLED_TEXT}; }}
QPushButton#danger {{ background: {RED}; color: white; font-weight: 600; }}
QPushButton#danger:pressed {{ background: {RED_PRESSED}; }}
QPushButton#danger:disabled {{ background: {DISABLED_BG}; color: {DISABLED_TEXT}; }}
QPushButton#choice[active="true"] {{ background: {BABY_BLUE}; color: {INK}; font-weight: 600; }}
QToolButton#estop {{ background: {RED}; border-radius: 12px; }}
QToolButton#estop:pressed {{ background: {RED_PRESSED}; }}
"""
