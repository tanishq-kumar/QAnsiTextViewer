"""Render the docs' proof screenshots from the real widget.

Run with ``QT_QPA_FONTDIR=C:/Windows/Fonts uv run python tools/make_screenshots.py``
(the offscreen platform needs a font directory). Every image is a
``QWidget.grab()`` of an actual ``AnsiTextViewer``; nothing is drawn by hand.
"""

import os
import re
import sys
import textwrap
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from darkmode import suffixed, use_theme
from PySide6.QtWidgets import QApplication

from ansi_text_viewer import AnsiTextViewer

DOCS = Path(__file__).resolve().parent.parent / "docs"
OUT = DOCS / "assets"


def sgr(code: str) -> str:
    """Return the escape sequence for SGR *code*."""
    return f"\x1b[{code}m"


RESET, BOLD, GRAY = sgr("0"), sgr("1"), sgr("90")
RED, GREEN, YELLOW = sgr("31"), sgr("32"), sgr("33")
ORANGE = sgr("38;5;208")

STREAM = [
    f"{GRAY}09:41:02{RESET} [INFO]  build: configuring "
    f"{BOLD}qansitextviewer{RESET} 0.1.2",
    f"{GRAY}09:41:02{RESET} [INFO]  collected {BOLD}214{RESET} tests",
    f"{GRAY}09:41:03{RESET} [DEBUG] QT_QPA_PLATFORM=offscreen",
    f"tests/test_search.py {GREEN}....................{RESET} {GREEN}[ 38%]{RESET}",
    f"tests/test_async.py {GREEN}.........{YELLOW}s{GREEN}.........{RESET} "
    f"{GREEN}[ 71%]{RESET}",
    f"{GRAY}09:41:05{RESET} [WARN]  slow test: test_burst_100k took 2.41s",
    f"tests/test_session.py {GREEN}......{RED}F{GREEN}...{RESET} {RED}[100%]{RESET}",
    f"{GRAY}09:41:06{RESET} [ERROR] test_load_session: timeout after 30s",
    "Traceback (most recent call last):",
    '  File "tests/test_session.py", line 88, in test_load_session',
    f"{ORANGE}Uploading report...{RESET} 10%\r{ORANGE}Uploading report...{RESET} 100%",
    f"{GRAY}09:41:07{RESET} [INFO]  report: https://example.com/runs/1842",
    f"{sgr('1;31')}1 failed{RESET}, {GREEN}212 passed{RESET}, "
    f"{YELLOW}1 skipped{RESET} in 6.92s",
]

NAMES = ["red", "green", "yellow", "blue", "magenta", "cyan"]


def shoot(viewer: AnsiTextViewer, name: str) -> None:
    """Show *viewer*, grab it to ``docs/assets/<name>`` and close it."""
    viewer.show()
    QApplication.processEvents()
    viewer.grab().save(str(OUT / name))
    viewer.close()


def hero(theme: str, name: str) -> None:
    """Render a test run with log levels, a search match and a bookmark."""
    viewer = AnsiTextViewer()
    viewer.setTheme(theme)
    viewer.setLogLevelHighlighting(True)
    viewer.setMonospaceFont("Consolas", 11)
    viewer.resize(820, 292)
    viewer.appendAnsiText("\n".join(STREAM) + "\n")
    viewer.highlight_search("timeout")
    viewer.toggleBookmark(7)
    shoot(viewer, name)


def palette(name: str, theme: str) -> None:
    """Render styles, the 16 base colors, 256-color and truecolor."""
    viewer = AnsiTextViewer()
    viewer.setTheme(theme)
    viewer.setMonospaceFont("Consolas", 11)
    viewer.resize(400, 222)
    styles = [("1", "bold"), ("3", "italic"), ("4", "underline")]
    styles += [("7", "reverse"), ("9", "strike")]
    ramp = "".join(f"{sgr(f'48;5;{c}')} " for c in range(16, 232, 6))
    gray = "".join(f"{sgr(f'48;5;{c}')} " for c in range(232, 256))
    true = "".join(
        sgr(f"48;2;{255 * i // 35};{120 + 100 * j // 35};{255 * j // 35}") + " "
        for i, j in ((i, 35 - i) for i in range(36))
    )
    lines = [
        " ".join(f"{sgr(c)}{label}{RESET}" for c, label in styles),
        " ".join(f"{sgr(str(31 + i))}{n}{RESET}" for i, n in enumerate(NAMES)),
        " ".join(f"{sgr(str(91 + i))}{n}{RESET}" for i, n in enumerate(NAMES)),
        f"{ORANGE}256-color 208{RESET} {sgr('38;5;45')}045{RESET} "
        f"{sgr('38;5;170')}170{RESET}",
        ramp + RESET,
        gray + RESET,
        f"{sgr('38;2;255;121;198')}truecolor #ff79c6{RESET} "
        f"{sgr('38;2;80;250;123')}#50fa7b{RESET}",
        true + RESET,
        f"{sgr('30;43')} WARN {RESET} {sgr('97;41')} FAIL {RESET} "
        f"{sgr('30;42')} PASS {RESET}",
    ]
    viewer.appendAnsiText("\n".join(lines) + "\n")
    shoot(viewer, suffixed(name, theme))


def quickstart(name: str, theme: str) -> None:
    """Run the home page's ``quickstart.py`` listing and grab the viewer.

    The listing asks for ``setTheme("auto")``, which follows the OS; each
    pass renders the case where the OS is in *theme*.
    """
    page = (DOCS / "index.md").read_text(encoding="utf-8")
    block = re.search(r'```python title="quickstart.py"[^\n]*\n(.*?)\n```', page, re.S)
    code = block.group(1)
    code = code.replace("app = QApplication([])", "").replace("app.exec()", "")
    assert 'setTheme("auto")' in code, "quickstart no longer uses the auto theme"
    code = code.replace('setTheme("auto")', f'setTheme("{theme}")')
    scope: dict = {}
    exec(code, scope)  # noqa: S102 - trusted repository docs
    viewer = scope["viewer"]
    viewer.setMonospaceFont("Consolas", 11)
    viewer.resize(420, 110)
    shoot(viewer, suffixed(name, theme))


def guide_window(name: str, theme: str = "light") -> None:
    """Run the first guide's assembled ``log_window.py`` and grab its window.

    The code is read from the guide itself, so the picture cannot drift from
    the listing readers copy.
    """
    guide = (DOCS / "guides" / "first-log-pane.md").read_text(encoding="utf-8")
    block = re.search(r"\?\?\? example.*?```python[^\n]*\n(.*?)\n\s*```", guide, re.S)
    code = textwrap.dedent(block.group(1))
    code = code.replace("app = QApplication([])", "").replace("app.exec()", "")
    scope: dict = {}
    exec(code, scope)  # noqa: S102 - trusted repository docs
    window = scope["window"]
    window.viewer.setMonospaceFont("Consolas", 11)
    window.resize(640, 220)
    window.search.setText("timeout")
    shoot(window, suffixed(name, theme))


def themes(name: str) -> None:
    """Render the same short log in the light and dark themes."""
    text = (
        f"{GRAY}09:41:02{RESET} [INFO]  server up\n"
        f"{GRAY}09:41:05{RESET} [WARN]  retrying connection\n"
        f"{GRAY}09:41:06{RESET} [ERROR] timeout after 30s\n"
        "plain text follows the theme\n"
    )
    for theme in ("light", "dark"):
        viewer = AnsiTextViewer()
        viewer.setTheme(theme)
        viewer.setLogLevelHighlighting(True)
        viewer.setMonospaceFont("Consolas", 11)
        viewer.resize(340, 118)
        viewer.appendAnsiText(text)
        shoot(viewer, f"{name}_{theme}.png")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    hero("dark", "hero_dark.png")
    hero("light", "hero_light.png")
    for theme in ("light", "dark"):
        use_theme(app, theme)
        palette("ansi_palette.png", theme)
        quickstart("quickstart_output.png", theme)
        guide_window("guide_log_window.png", theme)
    use_theme(app, "light")
    themes("theme")
    print("wrote hero, palette, guide window, and theme screenshots")
