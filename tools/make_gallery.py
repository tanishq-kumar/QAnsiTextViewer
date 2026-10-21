"""Render the Visual tour screenshots from the real demo window.

Run with ``QT_QPA_FONTDIR=C:/Windows/Fonts uv run python tools/make_gallery.py``
(the offscreen platform needs a font directory). Every image is a grab of
``demo.TestWindow`` driven into the state the tour describes; the red callout
boxes are painted from the widgets' real geometry. Random log content is
seeded and timestamps are fixed, so reruns produce the same pictures.
"""

import logging
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from darkmode import suffixed, use_theme  # noqa: E402
from PySide6.QtCore import QPoint, QRect, QTimer  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QContextMenuEvent,
    QFont,
    QPainter,
    QPen,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

import demo  # noqa: E402

OUT = ROOT / "docs" / "assets"
SIZE = (1172, 730)
CALLOUT = QColor(220, 30, 30)
FACTS: dict = {}
THEME = "light"  # set per pass in __main__


class FixedClock(logging.Filter):
    """Stamp records with a fixed, advancing time so reruns match."""

    def __init__(self):
        """Start the clock at a fixed epoch (printed in local time)."""
        super().__init__()
        self.t = 1760000000.0

    def filter(self, record):
        """Assign the next timestamp to *record* and let it through."""
        record.created = self.t
        self.t += 1.7
        return True


def window() -> demo.TestWindow:
    """Build a demo window at the tour's size with deterministic logs."""
    random.seed(7)
    win = demo.TestWindow()
    for handler in win.logger.handlers:
        handler.filters.clear()
        handler.addFilter(FixedClock())
    win.viewer.setMonospaceFont("Consolas", 10)
    win.font_combo.setCurrentFont(QFont("Consolas"))
    if THEME == "dark":
        win.theme_combo.setCurrentText("Dark")
    win.resize(*SIZE)
    win.show()
    settle()
    return win


def settle() -> None:
    """Let layouts and deferred paints finish."""
    for _ in range(3):
        QApplication.processEvents()


def logs(win: demo.TestWindow, n: int) -> None:
    """Emit *n* seeded random log records."""
    for _ in range(n):
        win.generate_random_log()
    settle()


def widget_rect(win: QWidget, *widgets: QWidget) -> QRect:
    """Return the union of *widgets*' rectangles in window coordinates."""
    rect = QRect()
    for w in widgets:
        rect = rect.united(QRect(w.mapTo(win, QPoint(0, 0)), w.size()))
    return rect


def line_rect(win: demo.TestWindow, block: int) -> QRect:
    """Return the full-width rectangle of text *block* in window coordinates."""
    viewer = win.viewer
    cursor = QTextCursor(viewer.document().findBlockByNumber(block))
    r = viewer.cursorRect(cursor)
    vp = viewer.viewport()
    top_left = vp.mapTo(win, QPoint(0, r.top()))
    return QRect(top_left, QPoint(vp.mapTo(win, QPoint(vp.width(), r.bottom()))))


def save(win: QWidget, name: str, boxes=(), overlay=None) -> None:
    """Grab *win*, paint callout *boxes* and an optional overlay, and save."""
    pix = win.grab()
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if overlay is not None:
        painter.drawPixmap(overlay[0], overlay[1])
    pen = QPen(CALLOUT, 3)
    painter.setPen(pen)
    for box in boxes:
        painter.drawRect(box.adjusted(-3, -3, 3, 3))
    painter.end()
    pix.save(str(OUT / suffixed(name, THEME)))
    win.close()


def shot_board() -> None:
    """The whole window, empty."""
    save(window(), "demo_screen_with_all_functions_empty_logs.png")


def shot_ansi() -> None:
    """Test ANSI Colors output, scrolled to the top."""
    win = window()
    win.run_test()
    win.viewer.verticalScrollBar().setValue(0)
    settle()
    save(win, "demo_screen_with_ANSI_escape_code.png")


def shot_stream() -> None:
    """Streamed logs, a finished progress line, links, current line."""
    win = window()
    win.curline_cb.setChecked(True)
    logs(win, 6)
    win.run_progress_test()
    logs(win, 18)
    cursor = QTextCursor(win.viewer.document().findBlockByNumber(9))
    win.viewer.setTextCursor(cursor)
    settle()
    FACTS["stream_progress_line"] = 7
    save(win, "demo_screen_with_streaming_logs_and_number_line.png")


def shot_search() -> None:
    """Highlight search with the query field and counter boxed."""
    win = window()
    logs(win, 40)
    win.search_input.setText("Timeout")
    settle()
    FACTS["search_matches"] = win.total_matches
    win.viewer.verticalScrollBar().setValue(0)
    settle()
    save(
        win,
        "demo_screen_with_highlight_search.png",
        boxes=[
            widget_rect(win, win.search_input),
            widget_rect(win, win.btn_prev, win.btn_next, win.match_label),
        ],
    )


def bookmarked(win: demo.TestWindow) -> list[int]:
    """Fill the view and bookmark two lines; return their block numbers."""
    logs(win, 40)
    win.viewer.verticalScrollBar().setValue(0)
    lines = [6, 11]
    for block in lines:
        win.viewer.toggleBookmark(block)
    settle()
    return lines


def shot_bookmarks() -> None:
    """Bookmarked lines in the view and in the list panel."""
    win = window()
    lines = bookmarked(win)
    FACTS["bookmark_lines"] = [b + 1 for b in lines]
    save(
        win,
        "demo_screen_with_bookmarks.png",
        boxes=[line_rect(win, lines[0]), widget_rect(win, win.bm_list)],
    )


def shot_context_menu() -> None:
    """The right-click menu, grabbed from its popup and composited."""
    win = window()
    logs(win, 20)
    win.viewer.verticalScrollBar().setValue(0)
    settle()
    vp = win.viewer.viewport()
    local = QPoint(420, 120)
    captured = {}

    def grab_popup():
        popup = QApplication.activePopupWidget()
        if popup is not None:
            captured["pix"] = popup.grab()
            captured["pos"] = win.mapFromGlobal(popup.mapToGlobal(QPoint(0, 0)))
            popup.close()

    QTimer.singleShot(400, grab_popup)
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, local, vp.mapToGlobal(local)
    )
    win.viewer.contextMenuEvent(event)
    settle()
    overlay = (captured["pos"], captured["pix"]) if captured else None
    save(win, "demo_screen_with_context_menu.png", overlay=overlay)


def shot_selection() -> None:
    """A multi-line selection with its live statistics boxed."""
    win = window()
    bookmarked(win)
    doc = win.viewer.document()
    cursor = QTextCursor(doc.findBlockByNumber(3))
    end = doc.findBlockByNumber(12)
    cursor.setPosition(
        end.position() + end.length() - 1, QTextCursor.MoveMode.KeepAnchor
    )
    win.viewer.setTextCursor(cursor)
    settle()
    FACTS["selection"] = win.stats_label.text()
    save(
        win,
        "demo_screen_with_highlight_text_selection.png",
        boxes=[widget_rect(win, win.stats_label)],
    )


def shot_system_font() -> None:
    """Proportional rendering after pressing System font."""
    QApplication.setFont(QFont("Segoe UI", 9))
    win = window()
    logs(win, 24)
    win.use_system_font()
    win.viewer.verticalScrollBar().setValue(0)
    settle()
    save(
        win,
        "demo_screen_with_system_fonts.png",
        boxes=[widget_rect(win, win.font_system)],
    )
    QApplication.setFont(QFont("Segoe UI", 9))


LONG = (
    "Fetching data from endpoint '/api/v1/users' with filter "
    "status=active&region=eu-west&include=profile,settings,permissions "
    "returned 2048 rows in 312ms from table 'users'."
)


def shot_wrap(enabled: bool, name: str) -> None:
    """The same long lines with word wrap off or on."""
    win = window()
    win.logger.info(LONG)
    logs(win, 4)
    win.logger.warning(LONG)
    logs(win, 4)
    win.wrap_cb.setChecked(enabled)
    win.viewer.verticalScrollBar().setValue(0)
    settle()
    save(win, name, boxes=[widget_rect(win, win.wrap_cb)])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    for THEME in ("light", "dark"):
        use_theme(app, THEME)
        app.setFont(QFont("Segoe UI", 9))
        shot_board()
        shot_ansi()
        shot_stream()
        shot_search()
        shot_bookmarks()
        shot_context_menu()
        shot_selection()
        shot_system_font()
        shot_wrap(False, "demo_screen_before_wrap_text.png")
        shot_wrap(True, "demo_screen_after_wrap_text.png")
        print(THEME, FACTS)
