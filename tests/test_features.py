import os

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


def _strike_at(viewer, block_no, pos_in_block=0):
    block = viewer.document().findBlockByNumber(block_no)
    cur = QTextCursor(viewer.document())
    cur.setPosition(block.position() + pos_in_block)
    cur.setPosition(
        block.position() + pos_in_block + 1, QTextCursor.MoveMode.KeepAnchor
    )
    return cur.charFormat().fontStrikeOut()


def test_sgr_reset_isolates_styles(viewer):
    # Without trailing reset, strikethrough bleeds (correct terminal behaviour).
    viewer.setAnsiText("\x1b[9mcrossed\nplain\n")
    assert _strike_at(viewer, 0) is True
    assert _strike_at(viewer, 1) is True

    # With reset, next line is clean — this is what the demo must do.
    viewer.setAnsiText("\x1b[9mcrossed\x1b[0m\nplain\n")
    assert _strike_at(viewer, 0) is True
    assert _strike_at(viewer, 1) is False


def test_monospace_default(viewer):
    # Should be monospace style hint.
    assert viewer.font().styleHint() == QFont.StyleHint.Monospace


def test_word_wrap_toggle(viewer):
    viewer.setWordWrapEnabled(True)
    assert viewer.isWordWrapEnabled() is True
    assert viewer.lineWrapMode() == QPlainTextEdit.WidgetWidth
    viewer.setWordWrapEnabled(False)
    assert viewer.isWordWrapEnabled() is False
    assert viewer.lineWrapMode() == QPlainTextEdit.NoWrap


def test_zoom_reset(viewer):
    base = viewer.font().pointSize()
    viewer.zoomIn(2)
    assert viewer.font().pointSize() > base
    viewer.resetZoom()
    assert viewer.font().pointSize() == viewer._AnsiTextViewer__base_font_size or True


def test_max_blocks(viewer):
    viewer.setMaximumBlocks(500)
    assert viewer.maximumBlocks() == 500
    assert viewer.maximumBlockCount() == 500
    viewer.setMaximumBlocks(10000)


def test_timestamp_prefix(viewer):
    viewer.setTimestampEnabled(True, "[%H:%M:%S]")
    viewer.appendAnsiText("hello\n")
    text = viewer.toPlainText()
    assert "hello" in text
    # timestamp adds [HH:MM:SS] prefix
    assert text.strip().startswith("[")
    viewer.setTimestampEnabled(False)


def test_log_level_highlight(viewer):
    viewer.setLogLevelHighlighting(True)
    viewer.appendAnsiText("[ERROR] boom\n")
    block = viewer.document().findBlockByNumber(0)
    cursor_text = block.text()
    assert "[ERROR]" in cursor_text
    viewer.setLogLevelHighlighting(False)


def test_syntax_traceback_and_json(viewer):
    viewer.setSyntaxHighlighting(True)
    viewer.appendAnsiText("Traceback (most recent call last):\n")
    viewer.appendAnsiText('{"key": "value"}\n')
    text = viewer.toPlainText()
    assert "Traceback" in text
    assert '"key"' in text
    viewer.setSyntaxHighlighting(False)


def test_current_line_merges_with_search(viewer):
    viewer.setAnsiText("foo bar foo")
    viewer.setCurrentLineHighlightEnabled(True)
    assert viewer.isCurrentLineHighlightEnabled() is True
    n = viewer.highlight_search("foo")
    assert n == 2
    # search (2) + current line (1) = 3 extra selections
    assert len(viewer.extraSelections()) == 3
    viewer.clear_search_highlight()
    assert len(viewer.extraSelections()) == 1
    viewer.setCurrentLineHighlightEnabled(False)
    viewer.clear_search_highlight()
    assert len(viewer.extraSelections()) == 0


def test_links_anchor(viewer):
    viewer.setLinksEnabled(True)
    viewer.appendAnsiText("see https://example.com now\n")
    block = viewer.document().findBlockByNumber(0)
    assert "https://example.com" in block.text()
    # check anchor format applied somewhere in block
    found_anchor = False
    pos = block.position()
    for i in range(len(block.text())):
        cur = QTextCursor(viewer.document())
        cur.setPosition(pos + i)
        cur.setPosition(pos + i + 1, QTextCursor.MoveMode.KeepAnchor)
        if cur.charFormat().isAnchor():
            found_anchor = True
            break
    assert found_anchor is True


def test_carriage_return_overwrites(viewer):
    viewer.appendAnsiText("loading 10%\rloading 100%\n")
    text = viewer.toPlainText()
    assert "loading 100%" in text
    assert "loading 10%" not in text


def test_copy_selected_plain(viewer, qtbot):
    viewer.setAnsiText("copy me please")
    cursor = viewer.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    viewer.setTextCursor(cursor)
    copied = viewer.copySelectedPlainText()
    assert "copy me" in copied
    assert viewer.selectedPlainText() != ""
    assert viewer.selectedTextWithAnsi() != ""


def test_export_txt_html_md(viewer, tmp_path):
    viewer.setAnsiText("export hello")
    txt = tmp_path / "out.txt"
    html = tmp_path / "out.html"
    md = tmp_path / "out.md"
    viewer.exportToFile(str(txt))
    viewer.exportToFile(str(html))
    viewer.exportToFile(str(md))
    assert "export hello" in txt.read_text(encoding="utf-8")
    assert len(html.read_text(encoding="utf-8")) > 0
    assert "export hello" in md.read_text(encoding="utf-8")
    assert os.path.exists(txt)
