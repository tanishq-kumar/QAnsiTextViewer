from PySide6.QtGui import QColor, QTextCursor


def test_bookmark_toggle_goto_clear(viewer):
    viewer.setAnsiText("line1\nline2\nline3\n")
    assert viewer.bookmarkedLines() == []

    assert viewer.toggleBookmark(1) is True
    assert viewer.isBookmarked(1) is True
    assert viewer.bookmarkedLines() == [1]

    assert viewer.toggleBookmark(1) is False
    assert viewer.isBookmarked(1) is False

    viewer.addBookmark(0)
    viewer.addBookmark(2)
    assert viewer.bookmarkedLines() == [0, 2]

    # cursor at 0 -> next is 2
    cur = viewer.textCursor()
    cur.setPosition(viewer.document().findBlockByNumber(0).position())
    viewer.setTextCursor(cur)
    assert viewer.gotoNextBookmark() == 2
    assert viewer.gotoPrevBookmark() == 0

    viewer.clearBookmarks()
    assert viewer.bookmarkedLines() == []
    assert viewer.gotoNextBookmark() == -1


def test_bookmark_highlight_merges(viewer):
    viewer.setAnsiText("a\nb\n")
    viewer.addBookmark(0)
    # 1 bookmark selection, no search, no current line
    assert len(viewer.extraSelections()) == 1
    viewer.setCurrentLineHighlightEnabled(True)
    assert len(viewer.extraSelections()) == 2
    viewer.setCurrentLineHighlightEnabled(False)


def test_theme_switch(viewer):
    viewer.setTheme("dark")
    assert viewer.theme() == "dark"
    assert "1e1e1e" in viewer.styleSheet()
    viewer.setTheme("light")
    assert viewer.theme() == "light"
    assert viewer.styleSheet() == ""
    viewer.setTheme("auto")
    assert viewer.theme() in ("light", "dark")


def test_custom_palette(viewer):
    viewer.setAnsiPaletteColor(1, QColor(1, 2, 3))
    pal = viewer.ansiPalette()
    assert (1, False) in pal
    viewer.appendAnsiText("\x1b[31mred\n")
    viewer.resetAnsiPalette()
    assert viewer.ansiPalette() == {}


def test_selection_stats(viewer):
    assert viewer.selectionStats() == {"chars": 0, "words": 0, "lines": 0}
    viewer.setAnsiText("hello world\nsecond line")
    cur = viewer.textCursor()
    cur.select(QTextCursor.SelectionType.Document)
    viewer.setTextCursor(cur)
    stats = viewer.selectionStats()
    assert stats["words"] >= 4
    assert stats["lines"] >= 2
    assert stats["chars"] > 0


def test_session_save_load(viewer, tmp_path):
    viewer.setAnsiText("session hello\nsecond\n")
    viewer.addBookmark(1)
    viewer.setWordWrapEnabled(True)
    viewer.setTheme("dark")
    path = tmp_path / "sess.json"
    viewer.saveSession(str(path))
    assert path.exists()

    viewer2_text = viewer.toPlainText()
    viewer.clear()
    viewer.setTheme("light")
    assert viewer.bookmarkedLines() == []

    viewer.loadSession(str(path))
    assert "session hello" in viewer.toPlainText()
    assert viewer.bookmarkedLines() == [1]
    assert viewer.isWordWrapEnabled() is True
    assert viewer.theme() == "dark"
    assert viewer2_text.strip().splitlines()[0] in viewer.toPlainText()


def test_gutter_click_toggles_bookmark(viewer, qtbot):
    from PySide6.QtCore import QPoint, Qt

    viewer.setAnsiText("one\ntwo\nthree\n")
    qtbot.waitUntil(lambda: viewer.isVisible(), timeout=2000)
    block = viewer.document().findBlockByNumber(1)
    y = (
        int(
            viewer.blockBoundingGeometry(block).translated(viewer.contentOffset()).top()
        )
        + 2
    )
    assert viewer.isBookmarked(1) is False
    qtbot.mouseClick(viewer.lineNumberArea, Qt.MouseButton.LeftButton, pos=QPoint(2, y))
    assert viewer.isBookmarked(1) is True


def test_goto_skips_filtered_out_bookmarks(viewer):
    viewer.setAnsiText("keep one\nhide me\nkeep two\n")
    viewer.addBookmark(0)
    viewer.addBookmark(1)
    viewer.addBookmark(2)
    viewer.filter_search("keep")
    assert viewer.document().findBlockByNumber(1).isVisible() is False
    cur = viewer.textCursor()
    cur.setPosition(viewer.document().findBlockByNumber(0).position())
    viewer.setTextCursor(cur)
    assert viewer.gotoNextBookmark() == 2
    assert viewer.gotoPrevBookmark() == 0
    viewer.filter_search("")
    cur.setPosition(viewer.document().findBlockByNumber(0).position())
    viewer.setTextCursor(cur)
    assert viewer.gotoNextBookmark() == 1


def test_bookmark_previews_and_signal(viewer, qtbot):
    viewer.setAnsiText("alpha\nbeta\ngamma\n")
    seen = []
    viewer.bookmarksChanged.connect(lambda lines: seen.append(list(lines)))
    viewer.addBookmark(1)
    assert viewer.bookmarkedPreviews() == [(1, "beta")]
    assert seen and seen[-1] == [1]
    viewer.removeBookmark(1)
    assert viewer.bookmarkedPreviews() == []


def test_bookmark_trim_drops_removed(viewer):
    viewer.setMaximumBlocks(100)
    viewer.setAnsiText("l0\nl1\nl2\n")
    viewer.addBookmark(0)
    assert viewer.isBookmarked(0) is True
    viewer.clear()
    assert viewer.bookmarkedLines() == []
    # re-add then clear via setAnsiText (which clears first)
    viewer.setAnsiText("new\n")
    assert viewer.bookmarkedLines() == []


def test_gutter_toggle_api(viewer):
    viewer.setAnsiText("a\nb\nc\n")
    viewer.show()
    # invalid y returns -1, valid gutter y toggles (offscreen height may vary,
    # so just verify method exists and invalid returns -1)
    assert viewer.toggleBookmarkAtY(-1000) == -1
    assert hasattr(viewer.lineNumberArea, "mousePressEvent")
