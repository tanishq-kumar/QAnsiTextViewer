"""Pluggable highlight rules: pure functions from text to style spans."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtGui import QColor

_URL_RE = re.compile(r"https?://[^\s)>\]]+")
_FILE_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|/|\./|../)?"
    r"(?:[\w.\-]+[\\/])+[\w.\-]+\.\w+"
    r"(?::\d+(?::\d+)?)?"
    r"|[\w.\-]+\.\w+:\d+(?::\d+)?"
)
_LOG_LEVEL_RE = re.compile(
    r"\[(ERROR|WARN(?:ING)?|INFO|DEBUG)\]"
    r"|\b(ERROR|WARNING|WARN|INFO|DEBUG):"
)
_JSON_KEY_RE = re.compile(r'"([^"\\]+)"\s*:')
_CMAKE_ERR_RE = re.compile(r"CMake\s+(Error|Warning|Deprecation).*", re.IGNORECASE)
_CMAKE_STATUS_RE = re.compile(
    r"--\s+(Configuring|Generating|Building|Installing|Up-to-date).*"
)
_CMAKE_BUILD_RE = re.compile(
    r"\[\s*\d+%\]\s+(Built target|Building|Linking|Scanning|Compiling).*"
)
_JUST_COMMENT_RE = re.compile(r"^\s{0,200}#.?.{0,500}")
_JUST_RECIPE_RE = re.compile(
    r"^([A-Za-z0-9_][A-Za-z0-9_-]{0,100})"
    r"(\s{0,10}\[[^\]\n]{0,100}\])?\s{0,10}:"
)
_JUST_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]{0,100})\s{0,10}(:=|\?=|=)")
_JUST_VAR_RE = re.compile(r"\{\{[^}\n]{1,100}\}\}")

_DEFAULT_LOG_LEVEL_COLORS = {
    "ERROR": QColor(200, 0, 0),
    "WARN": QColor(180, 120, 0),
    "WARNING": QColor(180, 120, 0),
    "INFO": QColor(0, 130, 0),
    "DEBUG": QColor(100, 100, 100),
}


@dataclass(frozen=True)
class Span:
    """A styled range inside one line (offsets are 0-based)."""

    start: int
    end: int
    foreground: QColor | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    anchor_href: str | None = None


class HighlightRule(Protocol):
    """Structural type for pluggable highlight rules."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield style spans for one line of *text*."""
        ...


class LogLevelRule:
    """Colors ``[ERROR]``/``WARN:``-style level markers bold."""

    def __init__(self, colors: dict[str, QColor] | None = None):
        """Create the rule, optionally overriding level colors.

        Args:
            colors: Level name to color, defaults to built-ins.
        """
        self.colors = dict(colors) if colors else dict(_DEFAULT_LOG_LEVEL_COLORS)

    def spans(self, text: str) -> Iterable[Span]:
        """Yield a bold span per level marker in *text*."""
        for m in _LOG_LEVEL_RE.finditer(text):
            level = next(g for g in m.groups() if g)
            color = self.colors.get(level, QColor(160, 0, 0))
            yield Span(m.start(), m.end(), foreground=color, bold=True)


class TracebackRule:
    """Marks Python ``Traceback`` lines red and bold."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield a whole-line span when *text* is a traceback header."""
        if "Traceback" in text:
            yield Span(0, len(text), foreground=QColor(180, 0, 0), bold=True)


class JsonKeyRule:
    """Colors JSON object keys blue."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield a span per ``"key":`` name in *text*."""
        for m in _JSON_KEY_RE.finditer(text):
            yield Span(m.start(1), m.end(1), foreground=QColor(0, 90, 180))


class CMakeRule:
    """Colors CMake errors, status lines and build progress."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield spans for CMake output in *text* (error wins over status)."""
        m = _CMAKE_ERR_RE.search(text)
        if m:
            if "error" in m.group(1).lower():
                color = QColor(200, 0, 0)
            else:
                color = QColor(180, 120, 0)
            yield Span(m.start(), m.end(), foreground=color, bold=True)
            return
        if _CMAKE_STATUS_RE.search(text):
            yield Span(0, len(text), foreground=QColor(0, 90, 180))
            return
        m = _CMAKE_BUILD_RE.search(text)
        if m:
            if "Built target" in m.group(0):
                color = QColor(0, 130, 0)
            else:
                color = QColor(90, 90, 90)
            yield Span(m.start(), m.end(), foreground=color)


class JustRule:
    """Colors justfile comments, recipes, assignments and variables."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield spans for justfile syntax in *text*."""
        if _JUST_COMMENT_RE.match(text):
            yield Span(0, len(text), foreground=QColor(120, 120, 120), italic=True)
            return
        m = _JUST_RECIPE_RE.match(text)
        if m:
            yield Span(m.start(1), m.end(1), foreground=QColor(0, 90, 180), bold=True)
        else:
            m = _JUST_ASSIGN_RE.match(text)
            if m:
                yield Span(
                    m.start(1), m.end(1), foreground=QColor(130, 0, 130), bold=True
                )
        for v in _JUST_VAR_RE.finditer(text):
            yield Span(v.start(), v.end(), foreground=QColor(160, 0, 160))


class UrlRule:
    """Turns ``http(s)://`` URLs into anchors."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield an underlined blue anchor span per URL in *text*."""
        for m in _URL_RE.finditer(text):
            url = m.group(0)
            yield Span(
                m.start(),
                m.end(),
                foreground=QColor(0, 80, 200),
                underline=True,
                anchor_href=url,
            )


class FileRule:
    """Turns ``path/to/file.py:line`` references into anchors."""

    def spans(self, text: str) -> Iterable[Span]:
        """Yield an anchor span per file reference (href drops ``:line``)."""
        for m in _FILE_RE.finditer(text):
            raw = m.group(0).rstrip(".,;:")
            if not raw or "://" in raw:
                continue
            file_part = re.split(r":\d+", raw, maxsplit=1)[0]
            yield Span(
                m.start(),
                m.start() + len(raw),
                foreground=QColor(0, 80, 200),
                underline=True,
                anchor_href=file_part,
            )
