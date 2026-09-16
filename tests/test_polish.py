from PySide6.QtGui import QTextCursor


def test_shortcut_signals_exist(viewer, qtbot):
    seen = []
    viewer.findRequested.connect(lambda: seen.append("find"))
    viewer.nextRequested.connect(lambda: seen.append("next"))
    viewer.prevRequested.connect(lambda: seen.append("prev"))
    viewer.findRequested.emit()
    viewer._shortcut_next()
    viewer._shortcut_prev()
    assert seen == ["find", "next", "prev"]


def test_shortcut_next_prev_navigate(viewer):
    viewer.setAnsiText("foo bar foo")
    assert viewer.highlight_search("foo") == 2
    assert viewer._shortcut_next() == 2
    assert viewer._shortcut_prev() == 1


def test_escape_clears_search(viewer):
    viewer.setAnsiText("foo foo")
    assert viewer.highlight_search("foo") == 2
    viewer.clear_search_highlight()
    assert viewer.searchExtraSelections() == []


def test_true_ansi_copy_roundtrip(viewer):
    viewer.setAnsiText("\x1b[31mred\x1b[0m plain\n")
    cur = viewer.textCursor()
    cur.select(QTextCursor.SelectionType.Document)
    viewer.setTextCursor(cur)
    ansi = viewer.selectedTextWithAnsi()
    plain = viewer.selectedPlainText()
    assert "red" in ansi and "plain" in ansi
    assert "\x1b[" in ansi  # real SGR present
    assert "31" in ansi  # red fg
    assert "\x1b[" not in plain


def test_ansi_copy_bold_and_truecolor(viewer):
    viewer.setAnsiText("\x1b[1mbold\x1b[0m \x1b[38;2;10;20;30mx\n")
    cur = viewer.textCursor()
    cur.select(QTextCursor.SelectionType.Document)
    viewer.setTextCursor(cur)
    ansi = viewer.selectedTextWithAnsi()
    assert "\x1b[1m" in ansi or ";1m" in ansi or "1;" in ansi or "1m" in ansi
    assert "38;2;10;20;30" in ansi


def test_ansi_copy_empty_without_selection(viewer):
    viewer.setAnsiText("hello")
    viewer.textCursor().clearSelection()
    assert viewer.selectedTextWithAnsi() == ""
    assert viewer.copySelectedWithAnsi() == ""


def test_file_path_link_anchored(viewer):
    viewer.setLinksEnabled(True)
    viewer.appendAnsiText('File "src/main.py:10" failed\n')
    block = viewer.document().findBlockByNumber(0)
    assert "src/main.py" in block.text()
    pos = block.position()
    idx = block.text().index("src/main.py")
    cur = QTextCursor(viewer.document())
    cur.setPosition(pos + idx)
    cur.setPosition(pos + idx + 1, QTextCursor.MoveMode.KeepAnchor)
    assert cur.charFormat().isAnchor() is True


def test_url_still_anchored_after_file_change(viewer):
    viewer.setLinksEnabled(True)
    viewer.appendAnsiText("see https://example.com and src/app.py:5\n")
    block = viewer.document().findBlockByNumber(0)
    text = block.text()
    assert "https://example.com" in text and "src/app.py" in text
    for needle in ("https://example.com", "src/app.py"):
        idx = text.index(needle)
        cur = QTextCursor(viewer.document())
        cur.setPosition(block.position() + idx)
        cur.setPosition(block.position() + idx + 1, QTextCursor.MoveMode.KeepAnchor)
        assert cur.charFormat().isAnchor() is True
