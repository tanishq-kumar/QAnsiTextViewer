"""Qt log viewer with ANSI escape decoding, search, and bookmarks."""

import logging
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from typing import cast

from PySide6.QtCore import QRect, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QKeySequence,
    QPainter,
    QShortcut,
    QTextBlockUserData,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QWidget

from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler
from ansi_text_viewer.highlight import (
    CMakeRule,
    FileRule,
    HighlightRule,
    JsonKeyRule,
    JustRule,
    LogLevelRule,
    TracebackRule,
    UrlRule,
)
from ansi_text_viewer.line_number_area import LineNumberArea
from ansi_text_viewer.search_handler import SearchHandler

# Mega-lines (e.g. 2MB minified JSON) skip per-block highlighting entirely:
# log lines are short; scanning them with ~10 regexes hangs the UI.
_HIGHLIGHT_MAX_LINE = 10000

logger = logging.getLogger(__name__)

_DARK_STYLESHEET = "QPlainTextEdit { background: #1e1e1e; color: #d4d4d4; }"

# Resolved dynamically: QFontDatabase.FixedFont exists at runtime but is
# missing from the Qt type stubs.
_FIXED_FONT = getattr(QFontDatabase, "FixedFont")

_TRUE_STRINGS = frozenset({"1", "true", "yes", "y", "on"})
_FALSE_STRINGS = frozenset({"0", "false", "no", "n", "off", ""})


def _to_bool(value: object) -> bool:
    """Interpret *value* strictly, understanding common strings."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
        raise ValueError(
            f"Cannot interpret {value!r} as bool; use True/False or 'true'/'false'."
        )
    return bool(value)


class _BookmarkData(QTextBlockUserData):
    pass


class AnsiTextViewer(QPlainTextEdit):
    r"""Read-only Qt widget that renders ANSI-encoded log text.

    Log content is untrusted by design: links open only on Ctrl+Click,
    cursor-movement counts are clamped, regex input is length-bounded,
    and lines over `maxLineLength` are truncated. For hostile logs also
    consider ``setLinksEnabled(False)``.

    Diagnostics: contract violations raise (`TypeError`/`ValueError`
    naming the offender); degraded-but-safe fallbacks log at DEBUG on
    the ``ansi_text_viewer`` logger instead of failing.

    Examples:
        >>> viewer = AnsiTextViewer()
        >>> viewer.appendAnsiText("\x1b[31mred\x1b[0m plain\n")
        >>> viewer.highlight_search("red")
        1
        >>> viewer.setTheme("dark")
    """

    bookmarksChanged = Signal(list)
    findRequested = Signal()
    nextRequested = Signal()
    prevRequested = Signal()
    asyncAppendProgress = Signal(int, int)
    asyncAppendFinished = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Create the viewer with terminal-like defaults.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.__ansi_escape_handler = AnsiEscapeHandler()
        self.__search_handler = SearchHandler(self)
        self.__bulk_depth = 0
        self.__bookmark_count = 0

        self.__line_numbers_visible = True
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth(0)

        self.__auto_scroll = True

        self.__is_paused = False
        self.__stream_buffer: list[str] = []
        self.__async_queue: deque[str] = deque()
        self.__async_total = 0
        self.__async_done = 0
        self.__async_scheduled = False
        self.__async_active = False

        self.__base_font_size = 10
        self._init_monospace_font()
        self.__word_wrap_enabled = False
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.__max_blocks = 10000
        self.setMaximumBlockCount(self.__max_blocks)
        self.__max_line_length = 10000

        self.__timestamp_enabled = False
        self.__timestamp_format = "[%H:%M:%S]"

        self.__log_level_enabled = False
        self.__log_rule = LogLevelRule()
        self.__syntax_highlight_enabled = False
        self.__syntax_rules: list[HighlightRule] = [
            TracebackRule(),
            JsonKeyRule(),
            CMakeRule(),
            JustRule(),
        ]
        self.__link_rules: list[HighlightRule] = [UrlRule(), FileRule()]
        self.__custom_rules: list[HighlightRule] = []

        self.__current_line_enabled = False
        self.__current_line_color = QColor(255, 255, 180, 90)
        self.__search_extra: list[QTextEdit.ExtraSelection] = []
        self.__refreshing_extra = False
        self.cursorPositionChanged.connect(self.__refresh_extra_selections)

        self.__links_enabled = True
        self.setMouseTracking(True)

        # Bookmarks live on the block itself so trim/filter cannot orphan them.
        self.__bookmark_color = QColor(140, 180, 255, 90)

        self.__theme = "light"
        self.__theme_requested = "light"
        self.__gutter_bg = QColor(240, 240, 240)
        self.__gutter_fg: QColor | Qt.GlobalColor = Qt.GlobalColor.darkGray
        self.__colors_follow_theme = True
        self._apply_theme("light")
        try:
            app = QApplication.instance()
            if isinstance(app, QApplication):
                hints = app.styleHints()
                if hasattr(hints, "colorSchemeChanged"):
                    hints.colorSchemeChanged.connect(self._on_system_scheme_changed)
        except Exception:
            pass

        self.__clear_on_start = False

        self.__sc_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.__sc_find.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.__sc_find.activated.connect(self.findRequested.emit)
        self.__sc_next = QShortcut(QKeySequence("F3"), self)
        self.__sc_next.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.__sc_next.activated.connect(self._shortcut_next)
        self.__sc_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self.__sc_prev.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.__sc_prev.activated.connect(self._shortcut_prev)
        self.__sc_esc = QShortcut(QKeySequence("Escape"), self)
        self.__sc_esc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.__sc_esc.activated.connect(self.clear_search_highlight)

    def _init_monospace_font(self):
        try:
            font = QFontDatabase.systemFont(_FIXED_FONT)
            font.setPointSize(self.__base_font_size)
        except Exception:
            font = QFont("Consolas", self.__base_font_size)
            font.setStyleHint(QFont.StyleHint.Monospace)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def setMonospaceFont(self, family: str | None = None, pointSize: int = 10):
        """Use a monospace font for the log view.

        Args:
            family: Font family name, or None for the system fixed font.
            pointSize: Point size, also stored as the zoom-reset size.

        Examples:
            >>> viewer.setMonospaceFont("Consolas", 11)
        """
        self.__base_font_size = pointSize
        if family:
            font = QFont(family, pointSize)
        else:
            try:
                font = QFontDatabase.systemFont(_FIXED_FONT)
                font.setPointSize(pointSize)
            except Exception:
                font = QFont("Consolas", pointSize)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def setFontSize(self, pointSize: int) -> None:
        """Set the point size, keeping it as the zoom-reset size.

        Args:
            pointSize: Clamped to 6..72; invalid input keeps the current size.

        Examples:
            >>> viewer.setFontSize(12)
        """
        try:
            size = int(pointSize)
        except (TypeError, ValueError):
            return
        clamped = max(6, min(size, 72))
        if clamped != size:
            logger.debug("setFontSize: clamped %r to %d", pointSize, clamped)
        self.__base_font_size = clamped
        font = self.font()
        font.setPointSize(clamped)
        self.setFont(font)

    def setFontFamily(self, family: str) -> None:
        """Set the font family, leaving the current size alone.

        Args:
            family: Installed family name; unknown names are ignored by Qt.

        Examples:
            >>> viewer.setFontFamily("Consolas")
        """
        if not family:
            return
        font = self.font()
        font.setFamily(str(family))
        self.setFont(font)

    def useSystemFont(self) -> None:
        """Adopt the global ``QApplication`` font as a one-shot snapshot.

        Later application-font changes are not tracked; call again or use
        :meth:`setMonospaceFont` to switch back.

        Examples:
            >>> viewer.useSystemFont()
        """
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        font = QFont(app.font())
        if font.pointSize() > 0:
            self.__base_font_size = max(6, min(font.pointSize(), 72))
            font.setPointSize(self.__base_font_size)
        self.setFont(font)

    def resetZoom(self):
        """Restore the font size from before zooming."""
        font = self.font()
        font.setPointSize(self.__base_font_size)
        self.setFont(font)

    def wheelEvent(self, event):
        """Zoom on Ctrl+Wheel, otherwise scroll normally."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn(1)
            elif delta < 0:
                self.zoomOut(1)
            event.accept()
            return
        super().wheelEvent(event)

    def setWordWrapEnabled(self, enabled: bool):
        """Toggle word wrap (off by default for log output).

        Args:
            enabled: True wraps at the widget edge, False scrolls sideways.
        """
        self.__word_wrap_enabled = _to_bool(enabled)
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if self.__word_wrap_enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def isWordWrapEnabled(self) -> bool:
        """Return True when word wrap is on."""
        return self.__word_wrap_enabled

    def setMaximumBlocks(self, n: int):
        """Cap kept lines for steady memory (default 10000, max 200000).

        Args:
            n: Maximum document blocks; clamped to 100..200000.
        """
        try:
            keep = int(n)
        except (TypeError, ValueError):
            keep = 10000
        clamped = max(100, min(keep, 200000))
        if clamped != keep:
            logger.debug("setMaximumBlocks: clamped %r to %d", n, clamped)
        self.__max_blocks = clamped
        self.setMaximumBlockCount(self.__max_blocks)

    def maximumBlocks(self) -> int:
        """Return the current maximum block count."""
        return self.__max_blocks

    def setMaxLineLength(self, n: int):
        """Cap single-line length.

        Longer lines are truncated with a marker. This bounds the
        per-character overhead (a 2MB single line spikes ~70MB otherwise).
        ``0`` disables truncation.

        Args:
            n: Maximum characters per line, clamped to 0..1000000.
        """
        try:
            keep = int(n)
        except (TypeError, ValueError):
            keep = 0
        clamped = max(0, min(keep, 1000000))
        if keep and clamped != keep:
            logger.debug("setMaxLineLength: clamped %r to %d", n, clamped)
        self.__max_line_length = clamped

    def maxLineLength(self) -> int:
        """Return the per-line character cap (0 means off)."""
        return self.__max_line_length

    def _truncate_lines(self, text: str) -> str:
        limit = self.__max_line_length
        if not limit or len(text) <= limit:
            # Fast path; still need per-line check only if some line is long.
            longest = max((len(line) for line in text.split("\n")), default=0)
            if "\n" not in text or longest <= limit:
                return text
        out = []
        for line in text.split("\n"):
            # A \r progress chunk shares the line; truncate each segment.
            segs = line.split("\r")
            for j, s in enumerate(segs):
                if len(s) > limit:
                    s = s[:limit] + f" … [truncated {len(s) - limit} chars]"
                segs[j] = s
            out.append("\r".join(segs))
        return "\n".join(out)

    def setTimestampEnabled(self, enabled: bool, fmt: str = "[%H:%M:%S]"):
        """Prefix each appended line with the current time.

        Args:
            enabled: Whether to timestamp new lines.
            fmt: `strftime` format for the prefix.
        """
        self.__timestamp_enabled = _to_bool(enabled)
        if fmt:
            self.__timestamp_format = fmt

    def isTimestampEnabled(self) -> bool:
        """Return True when timestamping is on."""
        return self.__timestamp_enabled

    def setLogLevelHighlighting(self, enabled: bool):
        """Color ``[ERROR]``/``[WARN]``/``[INFO]``/``[DEBUG]`` markers.

        Args:
            enabled: Whether to highlight newly appended blocks.
        """
        self.__log_level_enabled = _to_bool(enabled)

    def isLogLevelHighlighting(self) -> bool:
        """Return True when log-level highlighting is on."""
        return self.__log_level_enabled

    def setLogLevelColors(self, colors: dict) -> None:
        """Override level-name to color mapping for future highlights.

        Args:
            colors: e.g. ``{"ERROR": QColor(255, 0, 0)}``; unknown levels
                fall back to a dark red.

        Examples:
            >>> viewer.setLogLevelColors({"ERROR": QColor(200, 0, 0)})
        """
        self.__log_rule.colors = dict(colors)

    def logLevelColors(self) -> dict:
        """Return the current level-name to color mapping."""
        return dict(self.__log_rule.colors)

    def setSyntaxHighlighting(self, enabled: bool):
        """Highlight tracebacks, JSON keys, CMake and justfile syntax.

        Args:
            enabled: Whether to highlight newly appended blocks.
        """
        self.__syntax_highlight_enabled = _to_bool(enabled)

    def isSyntaxHighlighting(self) -> bool:
        """Return True when syntax highlighting is on."""
        return self.__syntax_highlight_enabled

    def _apply_timestamp(self, text: str) -> str:
        if not self.__timestamp_enabled or not text:
            return text
        prefix = datetime.now().strftime(self.__timestamp_format) + " "
        # Preserve trailing newline structure.
        ends_newline = text.endswith("\n")
        lines = text.split("\n")
        out = []
        for i, line in enumerate(lines):
            if i == len(lines) - 1 and line == "" and ends_newline:
                out.append("")
            elif line == "" and i == len(lines) - 1:
                out.append(line)
            else:
                # Don't timestamp pure carriage-return progress chunks here;
                # they are handled separately.
                out.append(prefix + line if line else line)
        return "\n".join(out)

    def add_highlight_rule(self, rule: HighlightRule) -> None:
        """Register a custom rule, applied after the built-in rules.

        Args:
            rule: Any object with a ``spans(text)`` method.

        Examples:
            >>> from ansi_text_viewer.highlight import HighlightRule
            >>> viewer.add_highlight_rule(MyRule())
        """
        self.__custom_rules.append(rule)

    def remove_highlight_rule(self, rule: HighlightRule) -> None:
        """Unregister a custom rule added with :meth:`add_highlight_rule`."""
        if rule in self.__custom_rules:
            self.__custom_rules.remove(rule)

    def highlight_rules(self) -> list[HighlightRule]:
        """Return the registered custom rules (built-ins excluded)."""
        return list(self.__custom_rules)

    def _highlight_block_range(self, start_block_number: int):
        rules: list[HighlightRule] = []
        if self.__log_level_enabled:
            rules.append(self.__log_rule)
        if self.__syntax_highlight_enabled:
            rules.extend(self.__syntax_rules)
        if self.__links_enabled:
            rules.extend(self.__link_rules)
        rules.extend(self.__custom_rules)
        if not rules:
            return
        doc = self.document()
        cursor = QTextCursor(doc)
        skipped = 0
        block = doc.findBlockByNumber(max(0, start_block_number))
        while block.isValid():
            text = block.text()
            if len(text) > _HIGHLIGHT_MAX_LINE:
                skipped += 1
                block = block.next()
                continue
            base = block.position()
            anchored: list[tuple[int, int]] = []
            for rule in rules:
                for s in rule.spans(text):
                    if s.anchor_href is not None:
                        if any(s.start < b and s.end > a for a, b in anchored):
                            continue
                        anchored.append((s.start, s.end))
                    cursor.setPosition(base + s.start)
                    cursor.setPosition(base + s.end, QTextCursor.MoveMode.KeepAnchor)
                    fmt = QTextCharFormat()
                    if s.foreground is not None:
                        fmt.setForeground(s.foreground)
                    if s.bold:
                        fmt.setFontWeight(QFont.Weight.Bold)
                    if s.italic:
                        fmt.setFontItalic(True)
                    if s.underline:
                        fmt.setFontUnderline(True)
                    if s.anchor_href is not None:
                        fmt.setAnchor(True)
                        fmt.setAnchorHref(s.anchor_href)
                    cursor.mergeCharFormat(fmt)
            block = block.next()
        if skipped:
            logger.debug(
                "highlight skipped %d lines over %d chars",
                skipped,
                _HIGHLIGHT_MAX_LINE,
            )

    def setCurrentLineHighlightEnabled(
        self, enabled: bool, color: QColor | None = None
    ):
        """Highlight the line under the text cursor.

        Merged with search highlights, never replacing them.

        Args:
            enabled: Whether to highlight the current line.
            color: Background color, or None to keep the default.
        """
        self.__current_line_enabled = _to_bool(enabled)
        if color is not None:
            self.__current_line_color = color
        self.__refresh_extra_selections()

    def isCurrentLineHighlightEnabled(self) -> bool:
        """Return True when current-line highlight is on."""
        return self.__current_line_enabled

    def currentLineColor(self) -> QColor:
        """Return the current-line highlight color."""
        return QColor(self.__current_line_color)

    def setExtraSelections(self, selections):
        """Store search selections, merged with line/bookmark highlights."""
        self.__search_extra = list(selections)
        self.__refresh_extra_selections()

    def searchExtraSelections(self):
        """Return the stored search selections (without merged extras)."""
        return list(self.__search_extra)

    def __refresh_extra_selections(self):
        if self.__refreshing_extra or self.__bulk_depth:
            return
        self.__refreshing_extra = True
        try:
            combined = list(self.__search_extra)
            doc = self.document()
            if self.__bookmark_count:
                for bno in self.bookmarkedLines():
                    block = doc.findBlockByNumber(bno)
                    if not block.isValid():
                        continue
                    sel = QTextEdit.ExtraSelection()
                    cur = QTextCursor(block)
                    cur.clearSelection()
                    fmt = QTextCharFormat()
                    fmt.setBackground(self.__bookmark_color)
                    fmt.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                    sel.format = fmt
                    sel.cursor = cur
                    combined.append(sel)
            if self.__current_line_enabled:
                sel = QTextEdit.ExtraSelection()
                sel.cursor = self.textCursor()
                sel.cursor.clearSelection()
                fmt = QTextCharFormat()
                fmt.setBackground(self.__current_line_color)
                fmt.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                sel.format = fmt
                combined.append(sel)
            super().setExtraSelections(combined)
        finally:
            self.__refreshing_extra = False

    def setLinksEnabled(self, enabled: bool):
        """Toggle clickable URLs and file paths (opened with Ctrl+Click).

        Args:
            enabled: False also hardens the viewer against hostile logs.
        """
        self.__links_enabled = _to_bool(enabled)

    def isLinksEnabled(self) -> bool:
        """Return True when clickable links are on."""
        return self.__links_enabled

    def mousePressEvent(self, event):
        """Open links only on Ctrl+Click; plain clicks just move the cursor."""
        if self.__links_enabled and event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                anchor = self.anchorAt(event.pos())
                if anchor:
                    if "://" in anchor or anchor.startswith("mailto:"):
                        url = QUrl(anchor)
                    else:
                        url = QUrl.fromLocalFile(anchor)
                    opened = QDesktopServices.openUrl(url)
                    logger.debug("open link %r -> %s", anchor, opened)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Show a pointing hand while hovering a link."""
        if self.__links_enabled:
            anchor = self.anchorAt(event.pos())
            if anchor:
                self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.viewport().unsetCursor()
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        """Build the right-click menu (copy, bookmarks, view, save)."""
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        copy_plain = menu.addAction("Copy Plain Text")
        copy_plain.triggered.connect(self.copySelectedPlainText)
        copy_ansi = menu.addAction("Copy With ANSI Codes")
        copy_ansi.triggered.connect(self.copySelectedWithAnsi)
        bm = menu.addAction("Toggle Bookmark")
        bm.triggered.connect(lambda: self.toggleBookmark())
        wrap = menu.addAction("Toggle Word Wrap")
        wrap.setCheckable(True)
        wrap.setChecked(self.__word_wrap_enabled)
        wrap.triggered.connect(
            lambda: self.setWordWrapEnabled(not self.__word_wrap_enabled)
        )
        lines = menu.addAction("Toggle Line Numbers")
        lines.setCheckable(True)
        lines.setChecked(self.__line_numbers_visible)
        lines.triggered.connect(
            lambda: self.setLineNumbersVisible(not self.__line_numbers_visible)
        )
        clear_act = menu.addAction("Clear")
        clear_act.triggered.connect(self.clear)
        save_act = menu.addAction("Save to File...")
        save_act.triggered.connect(self._save_via_dialog)
        menu.exec(event.globalPos())

    def selectedPlainText(self) -> str:
        """Return the selected text with paragraph separators as newlines."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return ""
        return cursor.selectedText().replace("\u2029", "\n")

    def copySelectedPlainText(self) -> str:
        """Copy the selection as plain text.

        Returns:
            The copied text, or "" when nothing is selected.
        """
        text = self.selectedPlainText()
        if text:
            QApplication.clipboard().setText(text)
        return text

    def selectedTextWithAnsi(self) -> str:
        """Reconstruct ANSI SGR from fragment formats (true ANSI copy)."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return ""
        sel_start, sel_end = cursor.selectionStart(), cursor.selectionEnd()
        doc = self.document()
        parts: list[str] = []
        block = doc.findBlock(sel_start)
        while block.isValid() and block.position() < sel_end:
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                f_start, f_end = frag.position(), frag.position() + frag.length()
                s, e = max(f_start, sel_start), min(f_end, sel_end)
                if s < e:
                    sub = frag.text()[s - f_start : e - f_start]
                    params = self._format_to_sgr_params(frag.charFormat())
                    if params:
                        parts.append(f"\x1b[{';'.join(map(str, params))}m{sub}\x1b[0m")
                    else:
                        parts.append(sub)
                it += 1
            block = block.next()
            if block.isValid() and block.position() < sel_end:
                parts.append("\n")
        return "".join(parts)

    def copySelectedWithAnsi(self) -> str:
        r"""Copy the selection with ANSI color codes reconstructed.

        Returns:
            The copied text with SGR sequences, or "" when empty.

        Examples:
            >>> viewer.setAnsiText("\x1b[31mred\x1b[0m\n")
            ... # select all, then:
            >>> "31m" in viewer.selectedTextWithAnsi()
            True
        """
        text = self.selectedTextWithAnsi()
        if text:
            QApplication.clipboard().setText(text)
        return text

    def _format_to_sgr_params(self, fmt: QTextCharFormat) -> list[int]:
        params: list[int] = []
        try:
            if fmt.fontWeight() >= QFont.Weight.Bold:
                params.append(1)
        except Exception:
            pass
        if fmt.fontItalic():
            params.append(3)
        if fmt.fontUnderline():
            params.append(4)
        if fmt.fontStrikeOut():
            params.append(9)
        default_fg, default_bg = self.__ansi_escape_handler.defaultColors()
        fg = fmt.foreground().color()
        bg = fmt.background().color()
        if fg != default_fg:
            params.extend(self._color_to_sgr(fg, foreground=True))
        if bg != default_bg:
            params.extend(self._color_to_sgr(bg, foreground=False))
        return params

    @staticmethod
    def _color_to_sgr(color: QColor, foreground: bool) -> list[int]:
        base = [
            (0, 0, 0),
            (170, 0, 0),
            (0, 170, 0),
            (170, 170, 0),
            (0, 0, 170),
            (170, 0, 170),
            (0, 170, 170),
            (170, 170, 170),
        ]
        rgb = (color.red(), color.green(), color.blue())
        for i, c in enumerate(base):
            if rgb == c:
                return [30 + i] if foreground else [40 + i]
            bright = (min(c[0] + 85, 255), min(c[1] + 85, 255), min(c[2] + 85, 255))
            if rgb == bright:
                return [90 + i] if foreground else [100 + i]
        if foreground:
            return [38, 2, rgb[0], rgb[1], rgb[2]]
        return [48, 2, rgb[0], rgb[1], rgb[2]]

    def exportToFile(self, path: str) -> str:
        """Save content to ``.txt``, ``.html`` or ``.md`` based on suffix.

        Args:
            path: Destination file path.

        Returns:
            The path that was written.
        """
        low = path.lower()
        if low.endswith(".html"):
            content = self.document().toHtml()
        elif low.endswith(".md"):
            content = "```text\n" + self.toPlainText() + "\n```\n"
        else:
            content = self.toPlainText()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _save_via_dialog(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "log.txt", "Text (*.txt);;HTML (*.html);;Markdown (*.md)"
        )
        if path:
            self.exportToFile(path)

    def _emit_bookmarks(self):
        try:
            self.bookmarksChanged.emit(self.bookmarkedLines())
        except Exception:
            pass

    @staticmethod
    def _drop_block_data(block) -> None:
        """Clear bookmark data; the stubs forbid None but Qt requires it."""
        block.setUserData(cast(QTextBlockUserData, None))

    def toggleBookmark(self, blockNumber: int | None = None) -> bool:
        """Bookmark or unbookmark a line.

        Bookmarks live on the block itself, so trimming or clearing the
        document can never leave stale numbers behind.

        Args:
            blockNumber: 0-based block, or None for the cursor line.

        Returns:
            True when a bookmark was added, False when removed.
        """
        if blockNumber is None:
            blockNumber = self.textCursor().blockNumber()
        block = self.document().findBlockByNumber(int(blockNumber))
        if not block.isValid():
            logger.debug("toggleBookmark: no block %r", blockNumber)
            return False
        if isinstance(block.userData(), _BookmarkData):
            self._drop_block_data(block)
            self.__bookmark_count -= 1
            added = False
        else:
            block.setUserData(_BookmarkData())
            self.__bookmark_count += 1
            added = True
        self.__refresh_extra_selections()
        self.lineNumberArea.update()
        self._emit_bookmarks()
        return added

    def toggleBookmarkAtY(self, y: int) -> int:
        """Toggle the bookmark on the visible block at gutter height *y*.

        Args:
            y: Vertical position inside the gutter widget.

        Returns:
            The toggled block number, or -1 when none is there.
        """
        block = self.firstVisibleBlock()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        while block.isValid():
            h = int(self.blockBoundingRect(block).height())
            if top <= y < top + h:
                if not block.isVisible():
                    return -1
                self.toggleBookmark(block.blockNumber())
                return block.blockNumber()
            top += h
            block = block.next()
        logger.debug("toggleBookmarkAtY: no visible block at y=%d", y)
        return -1

    def addBookmark(self, blockNumber: int):
        """Bookmark a 0-based block number (no-op when invalid)."""
        block = self.document().findBlockByNumber(int(blockNumber))
        if block.isValid() and not isinstance(block.userData(), _BookmarkData):
            block.setUserData(_BookmarkData())
            self.__bookmark_count += 1
            self.__refresh_extra_selections()
            self.lineNumberArea.update()
            self._emit_bookmarks()

    def removeBookmark(self, blockNumber: int):
        """Remove the bookmark on a 0-based block number."""
        block = self.document().findBlockByNumber(int(blockNumber))
        if block.isValid() and isinstance(block.userData(), _BookmarkData):
            self._drop_block_data(block)
            self.__bookmark_count -= 1
            self.__refresh_extra_selections()
            self.lineNumberArea.update()
            self._emit_bookmarks()

    def isBookmarked(self, blockNumber: int) -> bool:
        """Return True when the block carries a bookmark."""
        block = self.document().findBlockByNumber(int(blockNumber))
        return block.isValid() and isinstance(block.userData(), _BookmarkData)

    def bookmarkedLines(self) -> list[int]:
        """Return sorted 0-based numbers of bookmarked blocks."""
        out = []
        block = self.document().firstBlock()
        while block.isValid():
            if isinstance(block.userData(), _BookmarkData):
                out.append(block.blockNumber())
            block = block.next()
        return out

    def bookmarkedPreviews(self) -> list[tuple[int, str]]:
        """Return ``(block, first-80-chars)`` pairs for the bookmark list UI."""
        out = []
        block = self.document().firstBlock()
        while block.isValid():
            if isinstance(block.userData(), _BookmarkData):
                out.append((block.blockNumber(), block.text()[:80]))
            block = block.next()
        return out

    def clearBookmarks(self):
        """Remove every bookmark and notify listeners."""
        block = self.document().firstBlock()
        changed = False
        while block.isValid():
            if isinstance(block.userData(), _BookmarkData):
                self._drop_block_data(block)
                changed = True
            block = block.next()
        self.__bookmark_count = 0
        self.__refresh_extra_selections()
        self.lineNumberArea.update()
        if changed:
            self._emit_bookmarks()

    def setBookmarkColor(self, color: QColor) -> None:
        """Set the full-width background of bookmarked lines.

        Args:
            color: Background color (translucency recommended).

        Examples:
            >>> viewer.setBookmarkColor(QColor(140, 180, 255, 90))
        """
        self.__bookmark_color = QColor(color)
        self.__refresh_extra_selections()

    def bookmarkColor(self) -> QColor:
        """Return the bookmark highlight color."""
        return QColor(self.__bookmark_color)

    def _goto_bookmark(self, direction: int) -> int:
        ordered = self.bookmarkedLines()
        if not ordered:
            return -1
        doc = self.document()
        visible = [b for b in ordered if doc.findBlockByNumber(b).isVisible()]
        if not visible:
            return -1
        cur = self.textCursor().blockNumber()
        if direction > 0:
            nxt = [b for b in visible if b > cur]
            target = nxt[0] if nxt else visible[0]
        else:
            prv = [b for b in visible if b < cur]
            target = prv[-1] if prv else visible[-1]
        cursor = self.textCursor()
        cursor.setPosition(doc.findBlockByNumber(target).position())
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        return target

    def gotoNextBookmark(self) -> int:
        """Jump to the next bookmark, wrapping around.

        Filtered-out (invisible) bookmarks are skipped.

        Returns:
            The target block number, or -1 when none is reachable.
        """
        return self._goto_bookmark(1)

    def gotoPrevBookmark(self) -> int:
        """Jump to the previous bookmark, wrapping around.

        Filtered-out (invisible) bookmarks are skipped.

        Returns:
            The target block number, or -1 when none is reachable.
        """
        return self._goto_bookmark(-1)

    def setTheme(self, mode: str = "light"):
        """Apply the widget theme.

        Args:
            mode: ``"light"``, ``"dark"``, or ``"auto"`` (follows the OS
                and live-updates on system changes).

        Examples:
            >>> viewer.setTheme("dark")
        """
        mode = (mode or "light").lower()
        if mode not in ("light", "dark", "auto"):
            mode = "light"
        self.__theme_requested = mode
        self.__theme = self.__resolve_theme(mode)
        self._apply_theme(self.__theme)

    def theme(self) -> str:
        """Return the resolved theme (``"light"`` or ``"dark"``)."""
        return self.__theme

    def themeRequested(self) -> str:
        """Return the requested mode, including ``"auto"``."""
        return self.__theme_requested

    def __resolve_theme(self, mode: str) -> str:
        """Resolve "auto" against the OS color scheme."""
        if mode != "auto":
            return mode
        try:
            app = QApplication.instance()
            if not isinstance(app, QApplication):
                return "light"
            if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                return "dark"
            return "light"
        except Exception:
            return "light"

    def _on_system_scheme_changed(self, *args):
        if self.__theme_requested == "auto":
            self.__theme = self.__resolve_theme("auto")
            self._apply_theme(self.__theme)

    def setClearOnStart(self, enabled: bool):
        """Clear the view when :meth:`beginNewStream` starts a stream."""
        self.__clear_on_start = _to_bool(enabled)

    def isClearOnStart(self) -> bool:
        """Return True when new streams start cleared."""
        return self.__clear_on_start

    def beginNewStream(self):
        """Clear first if Clear-on-Start is on. Demo calls this on Start."""
        if self.__clear_on_start:
            self.clear()

    def _apply_theme(self, mode: str):
        """Apply stylesheet and gutter colors for *mode*."""
        if mode == "dark":
            self.setStyleSheet(_DARK_STYLESHEET)
            self.__gutter_bg = QColor(45, 45, 45)
            self.__gutter_fg = QColor(180, 180, 180)
        else:
            self.setStyleSheet("")
            self.__gutter_bg = QColor(240, 240, 240)
            self.__gutter_fg = Qt.GlobalColor.darkGray
        if self.__colors_follow_theme:
            if mode == "dark":
                self.__ansi_escape_handler.setDefaultColors(
                    QColor(212, 212, 212), QColor(30, 30, 30)
                )
            else:
                self.__ansi_escape_handler.setDefaultColors(
                    QColor(0, 0, 0), QColor(255, 255, 255)
                )
        self.lineNumberArea.update()

    def setAnsiPaletteColor(self, idx: int, color: QColor, bright: bool = False):
        """Override one of the eight ANSI base colors.

        Args:
            idx: Base color 0..7 (black, red, green, yellow, blue,
                magenta, cyan, white).
            color: Replacement color.
            bright: Whether it applies to the bright (90-97) variant.

        Examples:
            >>> viewer.setAnsiPaletteColor(1, QColor(255, 0, 0))
        """
        self.__ansi_escape_handler.setAnsi8Color(idx, color, bright)

    def resetAnsiPalette(self):
        """Restore the built-in ANSI palette."""
        self.__ansi_escape_handler.resetPalette()

    def ansiPalette(self) -> dict:
        """Return custom ``(index, bright) -> QColor`` overrides."""
        return self.__ansi_escape_handler.palette()

    def setDefaultColors(self, fg: QColor, bg: QColor) -> None:
        """Fix the SGR-reset text colors instead of following the theme.

        Args:
            fg: Default foreground for unstyled text.
            bg: Default background for unstyled text.

        Examples:
            >>> viewer.setDefaultColors(QColor(0, 0, 0), QColor(255, 255, 255))
        """
        self.__ansi_escape_handler.setDefaultColors(QColor(fg), QColor(bg))
        self.__colors_follow_theme = False

    def defaultColors(self) -> tuple[QColor, QColor]:
        """Return the current ``(foreground, background)`` defaults."""
        return self.__ansi_escape_handler.defaultColors()

    def setColorsFollowTheme(self, enabled: bool) -> None:
        """Follow the theme for default text colors.

        Args:
            enabled: True re-applies the current theme's pair at once.
        """
        self.__colors_follow_theme = _to_bool(enabled)
        if self.__colors_follow_theme:
            self._apply_theme(self.__theme)

    def colorsFollowTheme(self) -> bool:
        """Return True when default colors track the theme."""
        return self.__colors_follow_theme

    def selectionStats(self) -> dict:
        """Count the current selection.

        Returns:
            Dict with ``chars``, ``words`` and ``lines`` (zeros when empty).
        """
        text = self.selectedPlainText()
        if not text:
            return {"chars": 0, "words": 0, "lines": 0}
        return {
            "chars": len(text),
            "words": len(text.split()),
            "lines": text.count("\n") + 1,
        }

    def saveSession(self, path: str) -> str:
        """Save text, bookmarks and settings as JSON.

        Args:
            path: Destination ``.json`` file.

        Returns:
            The path that was written.
        """
        import json

        fg_default, bg_default = self.defaultColors()
        data = {
            "version": 2,
            "text": self.toPlainText(),
            "bookmarks": self.bookmarkedLines(),
            "bookmarkPreviews": self.bookmarkedPreviews(),
            "settings": {
                "wordWrap": self.__word_wrap_enabled,
                "timestamp": self.__timestamp_enabled,
                "logLevel": self.__log_level_enabled,
                "syntax": self.__syntax_highlight_enabled,
                "theme": self.__theme_requested,
                "maxBlocks": self.__max_blocks,
                "maxLineLength": self.__max_line_length,
                "currentLine": self.__current_line_enabled,
                "clearOnStart": self.__clear_on_start,
                "colorsFollowTheme": self.__colors_follow_theme,
                "defaultFg": [
                    fg_default.red(),
                    fg_default.green(),
                    fg_default.blue(),
                ],
                "defaultBg": [
                    bg_default.red(),
                    bg_default.green(),
                    bg_default.blue(),
                ],
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def loadSession(self, path: str) -> str:
        """Restore a session written by :meth:`saveSession`.

        Files over 10MB or with invalid content are rejected.

        Args:
            path: Source ``.json`` file.

        Returns:
            The path that was read.

        Raises:
            ValueError: When the file is too large or invalid.
        """
        import json
        import os

        if os.path.getsize(path) > 10 * 1024 * 1024:
            raise ValueError("session file too large (>10MB)")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("invalid session file")
        text = data.get("text", "")
        if not isinstance(text, str) or len(text) > 5 * 1024 * 1024:
            raise ValueError("invalid session text")
        settings = data.get("settings", {})
        if not isinstance(settings, dict):
            settings = {}
        self.setWordWrapEnabled(settings.get("wordWrap", False))
        self.setTimestampEnabled(settings.get("timestamp", False))
        self.setLogLevelHighlighting(settings.get("logLevel", False))
        self.setSyntaxHighlighting(settings.get("syntax", False))
        self.setTheme(settings.get("theme", "light"))
        self.setMaximumBlocks(settings.get("maxBlocks", 10000))
        if "maxLineLength" in settings:
            self.setMaxLineLength(settings.get("maxLineLength", 10000))
        self.setCurrentLineHighlightEnabled(settings.get("currentLine", False))
        self.setClearOnStart(settings.get("clearOnStart", False))
        self.setColorsFollowTheme(settings.get("colorsFollowTheme", True))
        if not self.colorsFollowTheme():
            fg = settings.get("defaultFg")
            bg = settings.get("defaultBg")
            if (
                isinstance(fg, list)
                and isinstance(bg, list)
                and len(fg) == 3
                and len(bg) == 3
                and all(isinstance(c, int) for c in fg + bg)
            ):
                self.setDefaultColors(QColor(*fg), QColor(*bg))
        self.setAnsiText(text)
        self.clearBookmarks()
        bookmarks = data.get("bookmarks", [])
        if isinstance(bookmarks, list):
            for b in bookmarks[:10000]:
                try:
                    self.addBookmark(int(b))
                except (TypeError, ValueError):
                    continue
        return path

    def setAutoScroll(self, enabled: bool):
        """Scroll to the bottom as new output arrives."""
        self.__auto_scroll = _to_bool(enabled)

    def isAutoScroll(self) -> bool:
        """Return True when auto-scroll is on."""
        return self.__auto_scroll

    def setLineNumbersVisible(self, visible: bool):
        """Show or hide the gutter line numbers."""
        self.__line_numbers_visible = _to_bool(visible)
        self.lineNumberArea.setVisible(self.__line_numbers_visible)
        self.updateLineNumberAreaWidth(0)

    def isLineNumbersVisible(self) -> bool:
        """Return True when gutter line numbers are shown."""
        return self.__line_numbers_visible

    def setSearchHighlightColor(
        self, color: QColor, active_color: QColor | None = None
    ):
        """Set match backgrounds.

        Args:
            color: Background for inactive matches.
            active_color: Background for the active match, or None to
                leave it unchanged.

        Examples:
            >>> viewer.setSearchHighlightColor(QColor(255, 255, 0, 100))
        """
        self.__search_handler.setSearchHighlightColor(color, active_color)

    def searchHighlightColors(self) -> tuple[QColor, QColor]:
        """Return the ``(match, active)`` highlight colors."""
        handler = self.__search_handler
        return (
            QColor(handler.search_highlight_color),
            QColor(handler.active_search_color),
        )

    def highlight_search(
        self, query: str, use_regex: bool = False, match_case: bool = False
    ) -> int:
        """Highlight every match and jump to the first one.

        Over-long regexes are rejected to blunt ReDoS from untrusted input.

        Args:
            query: Text or pattern to find (empty clears the highlight).
            use_regex: Treat *query* as a regular expression.
            match_case: Case-sensitive matching.

        Returns:
            The number of matches found.

        Examples:
            >>> viewer.setAnsiText("foo bar foo")
            >>> viewer.highlight_search("foo")
            2
        """
        # Bound regex length to blunt ReDoS from untrusted search input.
        if use_regex and len(query or "") > 500:
            logger.debug("highlight_search: rejected %d-char regex", len(query or ""))
            return 0
        return self.__search_handler.highlight_search(query, use_regex, match_case)

    def filter_search(
        self, query: str, use_regex: bool = False, match_case: bool = False
    ):
        """Show only lines matching *query*; empty *query* restores all.

        Args:
            query: Text or pattern lines must contain.
            use_regex: Treat *query* as a regular expression.
            match_case: Case-sensitive matching.
        """
        if use_regex and len(query or "") > 500:
            logger.debug("filter_search: rejected %d-char regex", len(query or ""))
            query = ""
            use_regex = False
        self.__search_handler.apply_filter(query, use_regex, match_case)

    def next_match(self) -> int:
        """Jump to the next match, wrapping around.

        Returns:
            The 1-based index of the now-active match.
        """
        return self.__search_handler.next_match()

    def prev_match(self) -> int:
        """Jump to the previous match, wrapping around.

        Returns:
            The 1-based index of the now-active match.
        """
        return self.__search_handler.prev_match()

    def clear_search_highlight(self):
        """Clear all search highlights and selection state."""
        self.__search_handler.clear_search_highlight()

    def _shortcut_next(self):
        self.nextRequested.emit()
        return self.next_match()

    def _shortcut_prev(self):
        self.prevRequested.emit()
        return self.prev_match()

    def lineNumberAreaWidth(self):
        """Return the gutter width in pixels (0 when hidden)."""
        if not self.__line_numbers_visible:
            return 0
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        """Sync viewport margins with the gutter width."""
        if self.__bulk_depth:
            return
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect: QRect, dy: int):
        """Repaint or scroll the gutter after document updates."""
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(
                0, rect.y(), self.lineNumberArea.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        """Keep the gutter geometry in sync on resize."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        """Paint line numbers and bookmark markers in the gutter."""
        if not self.__line_numbers_visible:
            return

        painter = QPainter(self.lineNumberArea)
        painter.setFont(self.font())
        painter.fillRect(event.rect(), self.__gutter_bg)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(self.__gutter_fg)
                painter.drawText(
                    0,
                    top,
                    self.lineNumberArea.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    number,
                )
                if isinstance(block.userData(), _BookmarkData):
                    painter.fillRect(
                        0, top, 6, self.fontMetrics().height(), QColor(60, 120, 255)
                    )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def __execute_actions(self, actions, cursor):
        def _clamp(n, lo=0, hi=10000):
            try:
                return max(lo, min(int(n), hi))
            except (TypeError, ValueError):
                return lo

        for action in actions:
            cmd = action[0]
            if cmd == "text":
                cursor.insertText(action[1], action[2])
            elif cmd == "cursor_up":
                for _ in range(_clamp(action[1], 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Up)
            elif cmd == "cursor_down":
                for _ in range(_clamp(action[1], 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Down)
            elif cmd == "cursor_forward":
                for _ in range(_clamp(action[1], 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "cursor_back":
                for _ in range(_clamp(action[1], 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Left)
            elif cmd == "cursor_col":
                cursor.movePosition(cursor.MoveOperation.StartOfLine)
                for _ in range(_clamp(action[1] - 1, 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "cursor_pos":
                cursor.movePosition(cursor.MoveOperation.Start)
                for _ in range(_clamp(action[1] - 1, 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Down)
                for _ in range(_clamp(action[2] - 1, 0, 10000)):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "erase_screen":
                mode = action[1]
                if mode == 2:
                    self.clear()
                    cursor = self.textCursor()
                elif mode == 0:
                    cursor.movePosition(
                        cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 1:
                    cursor.movePosition(
                        cursor.MoveOperation.Start, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
            elif cmd == "erase_line":
                mode = action[1]
                if mode == 2:
                    cursor.movePosition(cursor.MoveOperation.StartOfLine)
                    cursor.movePosition(
                        cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 0:
                    cursor.movePosition(
                        cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 1:
                    cursor.movePosition(
                        cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
            elif cmd == "hide_cursor":
                self.setCursorWidth(0)
            elif cmd == "show_cursor":
                self.setCursorWidth(1)
        self.setTextCursor(cursor)

    def pause_stream(self):
        """Buffer appended text instead of displaying it."""
        self.__is_paused = True

    def resume_stream(self):
        """Flush buffered text and resume live display."""
        self.__is_paused = False
        if self.__stream_buffer:
            buffer_text = "".join(self.__stream_buffer)
            self.__stream_buffer.clear()
            self.__appendAnsiTextInternal(buffer_text)

    def appendAnsiTextAsync(self, text: str, chunk_lines: int = 500) -> None:
        """Queue text for non-blocking appends; returns immediately.

        Large bursts are split into line chunks inserted one per event-loop
        turn, so the UI never freezes. Order, ANSI state, timestamps and
        highlighting match the sync path. Must be called on the GUI thread;
        from worker threads, emit a signal connected to this slot instead.

        Args:
            text: Text to append (may contain newlines and ANSI codes).
            chunk_lines: Lines per event-loop turn, clamped to 1..10000.

        Raises:
            TypeError: When *text* is not a string.

        Examples:
            >>> viewer.appendAnsiTextAsync(huge_log)
            >>> viewer.asyncAppendFinished.connect(on_done)
        """
        if not isinstance(text, str):
            raise TypeError(
                f"appendAnsiTextAsync expects str, got {type(text).__name__}"
            )
        requested_chunks = chunk_lines
        try:
            want = int(chunk_lines)
        except (TypeError, ValueError):
            want = 500
        chunk_lines = max(1, min(want, 10000))
        if chunk_lines != want:
            logger.debug(
                "appendAnsiTextAsync: clamped chunk_lines %r to %d",
                requested_chunks,
                chunk_lines,
            )
        if not text:
            return
        segments = text.splitlines(keepends=True)
        # Never split right after a bare carriage return: the next segment
        # overwrites the current line, so it must stay in the same chunk.
        lines: list[str] = []
        for seg in segments:
            if lines and lines[-1].endswith("\r"):
                lines[-1] += seg
            else:
                lines.append(seg)
        for i in range(0, len(lines), chunk_lines):
            self.__async_queue.append("".join(lines[i : i + chunk_lines]))
        self.__async_total += len(lines)
        self.__async_active = True
        self.__schedule_async_pump()

    def hasPendingAppends(self) -> bool:
        """Return True while async chunks are still queued."""
        return bool(self.__async_queue)

    def cancelAsyncAppends(self) -> int:
        """Drop queued async chunks; the in-flight chunk still finishes.

        Returns:
            The number of dropped chunks.
        """
        dropped = len(self.__async_queue)
        self.__async_queue.clear()
        self.__async_total = 0
        self.__async_done = 0
        self.__async_active = False
        if dropped:
            logger.debug("cancelAsyncAppends: dropped %d chunks", dropped)
        return dropped

    def __schedule_async_pump(self) -> None:
        if not self.__async_scheduled and self.__async_queue:
            self.__async_scheduled = True
            QTimer.singleShot(0, self.__pump_async_queue)

    def __pump_async_queue(self) -> None:
        self.__async_scheduled = False
        if not self.__async_queue:
            return
        chunk = self.__async_queue.popleft()
        self.appendAnsiText(chunk)
        self.__async_done += chunk.count("\n")
        if self.__async_queue:
            self.asyncAppendProgress.emit(self.__async_done, self.__async_total)
            self.__schedule_async_pump()
        else:
            self.asyncAppendProgress.emit(self.__async_total, self.__async_total)
            self.__async_total = 0
            self.__async_done = 0
            if self.__async_active:
                self.__async_active = False
                self.asyncAppendFinished.emit()

    def appendAnsiText(self, text: str):
        r"""Append ANSI text; ``\r`` overwrites the current line (progress bars)."""
        if not isinstance(text, str):
            raise TypeError(f"appendAnsiText expects str, got {type(text).__name__}")
        if self.__is_paused:
            # Bound pause buffer so a hostile stream can't eat all RAM.
            self.__stream_buffer.append(text)
            if len(self.__stream_buffer) > 5000:
                dropped = len(self.__stream_buffer) - 5000
                del self.__stream_buffer[:dropped]
                logger.debug("pause buffer full: dropped %d oldest lines", dropped)
        else:
            self.__appendAnsiTextInternal(text)

    @contextmanager
    def _bulk_changes(self):
        """Suppress per-block UI churn; refresh once at the end."""
        self.__bulk_depth += 1
        outer = self.__bulk_depth == 1
        if outer:
            self.setUpdatesEnabled(False)
        try:
            yield
        finally:
            self.__bulk_depth -= 1
            if outer:
                self.setUpdatesEnabled(True)
                self.updateLineNumberAreaWidth(0)
                self.__refresh_extra_selections()

    def __appendAnsiTextInternal(self, text: str):
        # Normalize Windows newlines, keep \r for progress-bar handling.
        text = text.replace("\r\n", "\n")
        text = self._truncate_lines(text)
        if "\r" in text:
            self.__append_with_carriage_return(text)
            return
        with self._bulk_changes():
            text = self._apply_timestamp(text)
            old_count = max(0, self.document().blockCount() - 1)
            actions = self.__ansi_escape_handler.parse(text)
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.__execute_actions(actions, cursor)
            self.__search_handler.update_new_blocks(old_count)
            self._highlight_block_range(old_count)
            if self.__auto_scroll:
                self.ensureCursorVisible()

    def __append_with_carriage_return(self, text: str):
        # Split on \r: each chunk after the first overwrites current line.
        chunks = text.split("\r")
        with self._bulk_changes():
            self.__append_crlf_chunks(chunks)
            if self.__auto_scroll:
                self.ensureCursorVisible()

    def __append_crlf_chunks(self, chunks: list) -> None:
        r"""Insert pre-split \r chunks, overwriting the current line."""
        self.__appendAnsiTextInternal(chunks[0]) if chunks[0] else None
        for chunk in chunks[1:]:
            if chunk == "":
                # Bare \r: move to line start.
                cursor = self.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.movePosition(cursor.MoveOperation.StartOfLine)
                self.setTextCursor(cursor)
                continue
            # Overwrite current line then insert chunk (may contain \n).
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            # If chunk starts a new logical overwrite, clear current line first
            # unless chunk itself starts with \n.
            if not chunk.startswith("\n"):
                cursor.movePosition(cursor.MoveOperation.StartOfLine)
                cursor.movePosition(
                    cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor
                )
                cursor.removeSelectedText()
            self.setTextCursor(cursor)
            # Recurse without \r to handle timestamps/highlights.
            sub = chunk
            # Avoid infinite recursion: chunk has no \r by construction.
            sub = self._apply_timestamp(sub)
            old_count = max(0, self.document().blockCount() - 1)
            actions = self.__ansi_escape_handler.parse(sub)
            cur2 = self.textCursor()
            cur2.movePosition(cur2.MoveOperation.End)
            # If we just cleared the line, cursor is at end already; ensure
            # we insert at the cleared line start when sub has no leading \n.
            self.__execute_actions(actions, cur2)
            self.__search_handler.update_new_blocks(old_count)
            self._highlight_block_range(old_count)

    def setAnsiText(self, text: str):
        """Replace all content (clears bookmarks and search first)."""
        self.clear()
        self.appendAnsiText(text)

    def insertAnsiText(self, text: str):
        """Insert ANSI text at the current cursor position."""
        actions = self.__ansi_escape_handler.parse(text)
        cursor = self.textCursor()
        self.__execute_actions(actions, cursor)

    def clear(self):
        """Clear content, ANSI state, search, bookmarks and queued async."""
        super().clear()
        self.__ansi_escape_handler.reset()
        self.__search_extra = []
        # Bookmarks live on blocks, so clearing the document drops them.
        self.__bookmark_count = 0
        if self.__async_queue:
            logger.debug(
                "clear: dropped %d queued async chunks", len(self.__async_queue)
            )
            self.__async_queue.clear()
            self.__async_total = 0
            self.__async_done = 0
        self.__async_queue.clear()
        self.__async_total = 0
        self.__async_done = 0
        self.__refresh_extra_selections()
        # Keep SearchHandler state in sync without triggering another refresh loop.
        try:
            self.__search_handler.search_selections = []
            self.__search_handler.current_match_index = -1
        except Exception:
            pass
