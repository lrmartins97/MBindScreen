"""The light theme must stay readable: WCAG AA for text, 3:1 for icons and lines."""
import pytest
from lib.utils import theme


def luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize(
    "foreground, background",
    [
        (theme.TEXT, theme.BG),
        (theme.TEXT, theme.CARD),
        (theme.TEXT, theme.BUTTON),
        (theme.DIM, theme.BG),
        (theme.DIM, theme.CARD),
        (theme.INK, theme.BABY_BLUE),
        (theme.INK, theme.BABY_BLUE_PRESSED),
        (theme.GREEN, theme.CARD),
        ("#ffffff", theme.RED),
        (theme.DISABLED_TEXT, theme.DISABLED_BG),
    ],
)
def test_text_is_readable(foreground, background):
    assert contrast(foreground, background) >= 4.5


@pytest.mark.parametrize("background", [theme.BG, theme.CARD, theme.NAV, theme.TRACK])
def test_icons_and_lines_are_visible(background):
    assert contrast(theme.ACCENT, background) >= 3
