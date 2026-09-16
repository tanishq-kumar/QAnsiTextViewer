import time


def test_megaline_highlight_skipped_not_hung(viewer):
    viewer.setLogLevelHighlighting(True)
    viewer.setSyntaxHighlighting(True)
    viewer.setLinksEnabled(True)
    start = time.time()
    viewer.setAnsiText("x" * 2000000)
    assert time.time() - start < 10
    assert "x" * 100 in viewer.toPlainText()


def test_many_lines_trimmed(viewer):
    viewer.setMaximumBlocks(10000)
    viewer.setAnsiText("line\n" * 20000)
    assert viewer.document().blockCount() <= 10001


def test_none_input_raises_typeerror(viewer):
    try:
        viewer.appendAnsiText(None)
        assert False
    except TypeError:
        pass


def test_invalid_bookmarks_safe(viewer):
    viewer.setAnsiText("a\nb\n")
    assert viewer.toggleBookmark(-1) is False
    assert viewer.toggleBookmark(999999) is False
    assert viewer.isBookmarked(-1) is False
    assert viewer.gotoNextBookmark() == -1


def test_pause_buffer_bounded(viewer):
    viewer.pause_stream()
    for i in range(6000):
        viewer.appendAnsiText(f"line {i}\n")
    assert len(viewer._AnsiTextViewer__stream_buffer) <= 5000
    viewer.resume_stream()


def test_just_recipe_bounded():
    from ansi_text_viewer.highlight import JustRule

    assert list(JustRule().spans("x" * 2000000)) == []


def test_max_line_length_truncates(viewer):
    viewer.setMaxLineLength(100)
    viewer.setAnsiText("y" * 5000)
    text = viewer.toPlainText()
    assert len(text) < 5000
    assert "truncated" in text
    viewer.setMaxLineLength(10000)


def test_max_line_length_zero_disables(viewer):
    viewer.setMaxLineLength(0)
    viewer.setAnsiText("z" * 5000)
    assert "z" * 100 in viewer.toPlainText()
    viewer.setMaxLineLength(10000)
