import logging

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from demo import TestWindow

TestWindow.__test__ = False  # prevent pytest collecting the GUI class itself


@pytest.fixture
def win(qtbot):
    # Avoid duplicate log handlers across tests (same "TestLogger" name).
    logger = logging.getLogger("TestLogger")
    logger.handlers.clear()
    w = TestWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitUntil(lambda: w.isVisible(), timeout=2000)
    return w


def _button(win, text):
    for b in win.findChildren(QPushButton):
        if b.text() == text:
            return b
    raise AssertionError(f"button {text!r} not found")


def test_window_opens(win):
    assert win.isVisible()
    assert win.viewer is not None
    assert win.match_label.text() == "0/0"


def test_ansi_colors_button_flow(win, qtbot):
    btn = _button(win, "Test ANSI Colors")
    qtbot.mouseClick(btn, Qt.LeftButton)
    text = win.viewer.toPlainText()
    assert "fg red" in text
    assert "bg RGB coral" in text


def test_search_type_and_navigate(win, qtbot):
    win.viewer.setAnsiText("foo bar foo baz foo")
    qtbot.keyClicks(win.search_input, "foo")
    assert win.match_label.text() == "1/3"

    qtbot.mouseClick(win.btn_next, Qt.LeftButton)
    assert win.match_label.text() == "2/3"

    qtbot.mouseClick(win.btn_next, Qt.LeftButton)
    assert win.match_label.text() == "3/3"

    qtbot.mouseClick(win.btn_prev, Qt.LeftButton)
    assert win.match_label.text() == "2/3"


def test_search_regex_and_case_checkboxes(win, qtbot):
    win.viewer.setAnsiText("Foo foo FOO")
    qtbot.keyClicks(win.search_input, "foo")
    assert win.total_matches == 3

    qtbot.mouseClick(win.case_cb, Qt.LeftButton)
    assert win.case_cb.isChecked()
    assert win.total_matches == 1

    qtbot.mouseClick(win.case_cb, Qt.LeftButton)  # back off
    qtbot.mouseClick(win.regex_cb, Qt.LeftButton)
    assert win.regex_cb.isChecked()
    win.search_input.clear()
    qtbot.keyClicks(win.search_input, r"f.o")
    assert win.total_matches == 3


def test_filter_flow(win, qtbot):
    win.viewer.setAnsiText("keep this\nskip this\nkeep too\n")
    qtbot.keyClicks(win.filter_input, "keep")
    doc = win.viewer.document()
    assert doc.findBlockByNumber(0).isVisible() is True
    assert doc.findBlockByNumber(1).isVisible() is False

    win.filter_input.clear()
    assert doc.findBlockByNumber(1).isVisible() is True


def test_autoscroll_and_linenumbers_checkboxes(win, qtbot):
    assert win.autoscroll_cb.isChecked()
    qtbot.mouseClick(win.autoscroll_cb, Qt.LeftButton)
    assert not win.autoscroll_cb.isChecked()
    win.viewer.appendAnsiText("no-crash\n")

    qtbot.mouseClick(win.autoscroll_cb, Qt.LeftButton)
    assert win.autoscroll_cb.isChecked()

    assert win.line_numbers_cb.isChecked()
    qtbot.mouseClick(win.line_numbers_cb, Qt.LeftButton)
    assert win.viewer.lineNumberAreaWidth() == 0
    qtbot.mouseClick(win.line_numbers_cb, Qt.LeftButton)
    assert win.viewer.lineNumberAreaWidth() > 0


def test_clear_button(win, qtbot):
    win.viewer.setAnsiText("to be cleared")
    assert "to be cleared" in win.viewer.toPlainText()
    qtbot.mouseClick(win.clear_btn, Qt.LeftButton)
    assert win.viewer.toPlainText().strip() == ""


def test_stream_start_stop(win, qtbot):
    assert not win.log_timer.isActive()
    qtbot.mouseClick(win.stream_btn, Qt.LeftButton)
    assert win.stream_btn.isChecked()
    assert win.log_timer.isActive()
    assert "Stop" in win.stream_btn.text()

    # Generate one log synchronously instead of waiting 500ms.
    win.generate_random_log()
    assert len(win.viewer.toPlainText().strip()) > 0

    qtbot.mouseClick(win.stream_btn, Qt.LeftButton)
    assert not win.log_timer.isActive()
    assert "Start" in win.stream_btn.text()


def test_pause_resume_flow(win, qtbot):
    win.viewer.setAnsiText("base\n")
    qtbot.mouseClick(win.pause_btn, Qt.LeftButton)
    assert win.pause_btn.isChecked()
    assert "Resume" in win.pause_btn.text()

    win.viewer.appendAnsiText("buffered while paused\n")
    assert "buffered while paused" not in win.viewer.toPlainText()

    qtbot.mouseClick(win.pause_btn, Qt.LeftButton)
    assert not win.pause_btn.isChecked()
    assert "buffered while paused" in win.viewer.toPlainText()
