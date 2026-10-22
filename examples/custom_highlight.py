"""Add your own highlight rules: durations, HTTP status codes, IP addresses.

Run with ``uv run python examples/custom_highlight.py``. A rule is any
object with ``spans(text)`` that yields ``Span`` objects; it colors plain
log text that carries no ANSI codes of its own.
"""

import re
import sys
from collections.abc import Iterable

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from ansi_text_viewer import AnsiTextViewer
from ansi_text_viewer.highlight import Span


class DurationRule:
    """Bold orange for timings like ``41ms`` or ``2.5s``."""

    pattern = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s)\b")

    def spans(self, text: str) -> Iterable[Span]:
        """Yield one span per duration in *text*."""
        for m in self.pattern.finditer(text):
            yield Span(m.start(), m.end(), foreground=QColor(214, 110, 0), bold=True)


class StatusRule:
    """HTTP status codes: 2xx green, 3xx blue, 4xx amber, 5xx red."""

    pattern = re.compile(r"\" ([1-5]\d\d) ")
    colors = {
        "2": QColor(0, 140, 60),
        "3": QColor(30, 100, 200),
        "4": QColor(190, 120, 0),
        "5": QColor(200, 30, 30),
    }

    def spans(self, text: str) -> Iterable[Span]:
        """Yield a bold span on the status code of an access-log line."""
        m = self.pattern.search(text)
        if m and m.group(1)[0] in self.colors:
            color = self.colors[m.group(1)[0]]
            yield Span(m.start(1), m.end(1), foreground=color, bold=True)


class IpRule:
    """Dim the client address so the request stands out."""

    pattern = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}")

    def spans(self, text: str) -> Iterable[Span]:
        """Yield a gray span over a leading IPv4 address."""
        m = self.pattern.match(text)
        if m:
            yield Span(m.start(), m.end(), foreground=QColor(120, 120, 120))


ACCESS_LOG = """\
10.0.0.12 - - "GET /api/v1/users HTTP/1.1" 200 1532 41ms
10.0.0.12 - - "GET /static/app.js HTTP/1.1" 304 0 3ms
192.168.4.7 - - "POST /api/v1/login HTTP/1.1" 401 88 120ms
10.0.0.31 - - "GET /api/v1/reports?year=2026 HTTP/1.1" 200 90210 2.4s
192.168.4.7 - - "GET /old-page HTTP/1.1" 301 0 2ms
10.0.0.44 - - "POST /api/v1/upload HTTP/1.1" 502 0 30.0s
10.0.0.12 - - "DELETE /api/v1/users/17 HTTP/1.1" 204 0 18ms
"""


def build() -> AnsiTextViewer:
    """Create a viewer with the three custom rules and a sample access log."""
    viewer = AnsiTextViewer()
    viewer.setWindowTitle("Custom highlight rules")
    # Access logs are full of URL paths that are not local files; keep the
    # built-in file and URL link rules from underlining them.
    viewer.setLinksEnabled(False)
    for rule in (IpRule(), StatusRule(), DurationRule()):
        viewer.add_highlight_rule(rule)
    viewer.appendAnsiText(ACCESS_LOG)
    return viewer


def main() -> None:
    """Show the highlighted access log."""
    app = QApplication(sys.argv)
    viewer = build()
    viewer.resize(820, 300)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
