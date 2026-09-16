def test_append_plain_text(viewer):
    viewer.appendAnsiText("hello world")
    assert "hello world" in viewer.toPlainText()


def test_set_replaces_text(viewer):
    viewer.appendAnsiText("old")
    viewer.setAnsiText("new")
    text = viewer.toPlainText()
    assert "new" in text
    assert "old" not in text


def test_append_ansi_strips_codes_but_keeps_text(viewer):
    viewer.appendAnsiText("\x1b[31mred\x1b[0m plain")
    text = viewer.toPlainText()
    assert "red" in text
    assert "plain" in text
    assert "\x1b" not in text


def test_clear_empties(viewer):
    viewer.appendAnsiText("some text")
    viewer.clear()
    assert viewer.toPlainText().strip() == ""


def test_is_readonly(viewer):
    assert viewer.isReadOnly() is True


def test_pause_buffers_and_resume_flushes(viewer):
    viewer.pause_stream()
    viewer.appendAnsiText("buffered")
    assert "buffered" not in viewer.toPlainText()
    viewer.resume_stream()
    assert "buffered" in viewer.toPlainText()


def test_autoscroll_toggle_does_not_crash(viewer, qtbot):
    viewer.setAutoScroll(False)
    viewer.appendAnsiText("line1\n")
    viewer.setAutoScroll(True)
    viewer.appendAnsiText("line2\n")
    assert "line1" in viewer.toPlainText()


def test_line_numbers_toggle_width(viewer):
    viewer.setLineNumbersVisible(True)
    w_visible = viewer.lineNumberAreaWidth()
    assert w_visible > 0
    viewer.setLineNumbersVisible(False)
    assert viewer.lineNumberAreaWidth() == 0
    assert viewer.lineNumberArea.isVisible() is False


def test_erase_screen_clears(viewer):
    viewer.appendAnsiText("hello")
    viewer.appendAnsiText("\x1b[2J")
    assert viewer.toPlainText().strip() == ""


def test_highlight_search_counts_and_navigates(viewer):
    viewer.setAnsiText("foo bar foo baz foo")
    n = viewer.highlight_search("foo")
    assert n == 3
    assert viewer.next_match() == 2
    assert viewer.next_match() == 3
    assert viewer.prev_match() == 2
    viewer.clear_search_highlight()
    assert viewer.highlight_search("") == 0


def test_highlight_regex_and_case(viewer):
    viewer.setAnsiText("Foo foo FOO")
    assert viewer.highlight_search("foo") == 3
    assert viewer.highlight_search("foo", match_case=True) == 1
    assert viewer.highlight_search(r"f.o", use_regex=True) == 3


def test_filter_hides_non_matching_blocks(viewer):
    viewer.setAnsiText("keep this\nskip this\nkeep too\n")
    viewer.filter_search("keep")
    doc = viewer.document()
    b0 = doc.findBlockByNumber(0)
    b1 = doc.findBlockByNumber(1)
    b2 = doc.findBlockByNumber(2)
    assert b0.isVisible() is True
    assert b1.isVisible() is False
    assert b2.isVisible() is True
    # clearing filter restores all
    viewer.filter_search("")
    assert doc.findBlockByNumber(1).isVisible() is True
