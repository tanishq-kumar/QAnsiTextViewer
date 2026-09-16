"""Tests for the color configuration knobs."""

from PySide6.QtGui import QColor


def test_log_level_colors(viewer):
    assert "ERROR" in viewer.logLevelColors()
    viewer.setLogLevelColors({"ERROR": QColor(1, 2, 3)})
    assert viewer.logLevelColors()["ERROR"].red() == 1
    viewer.setLogLevelHighlighting(True)
    viewer.setAnsiText("[ERROR] boom\n")
    block = viewer.document().findBlockByNumber(0)
    assert "[ERROR]" in block.text()


def test_bookmark_color(viewer):
    viewer.setBookmarkColor(QColor(10, 20, 30, 40))
    assert viewer.bookmarkColor().red() == 10
    viewer.setAnsiText("a\nb\n")
    viewer.addBookmark(0)
    assert len(viewer.extraSelections()) == 1


def test_search_colors(viewer):
    match, active = viewer.searchHighlightColors()
    assert isinstance(match, QColor) and isinstance(active, QColor)
    viewer.setSearchHighlightColor(QColor(1, 2, 3), QColor(4, 5, 6))
    match, active = viewer.searchHighlightColors()
    assert (match.red(), active.red()) == (1, 4)
    viewer.setSearchHighlightColor(QColor(7, 8, 9))
    match, active = viewer.searchHighlightColors()
    assert (match.red(), active.red()) == (7, 4)


def test_current_line_color(viewer):
    assert isinstance(viewer.currentLineColor(), QColor)
    viewer.setCurrentLineHighlightEnabled(True, QColor(1, 2, 3, 4))
    assert viewer.currentLineColor().red() == 1
    assert len(viewer.extraSelections()) == 1
