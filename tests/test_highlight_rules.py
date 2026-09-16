"""Unit tests for highlight rules (pure logic, no widget needed)."""

from PySide6.QtGui import QColor, QTextCursor

from ansi_text_viewer.highlight import (
    CMakeRule,
    FileRule,
    JsonKeyRule,
    JustRule,
    LogLevelRule,
    Span,
    TracebackRule,
    UrlRule,
)


def test_span_is_value_type():
    assert Span(0, 5) == Span(0, 5)
    assert Span(0, 5) != Span(0, 6)


def test_log_level_rule():
    spans = list(LogLevelRule().spans("[ERROR] boom"))
    assert len(spans) == 1
    s = spans[0]
    assert (s.start, s.end) == (0, 7)
    assert s.bold is True
    assert (s.foreground.red(), s.foreground.green()) == (200, 0)
    assert list(LogLevelRule().spans("TERROR disaster")) == []
    assert list(LogLevelRule().spans("WARNING: low disk")) != []


def test_log_level_custom_colors():
    rule = LogLevelRule({"ERROR": QColor(1, 2, 3)})
    (s,) = rule.spans("[ERROR] x")
    assert (s.foreground.red(), s.foreground.green(), s.foreground.blue()) == (1, 2, 3)


def test_traceback_and_json_rules():
    (s,) = TracebackRule().spans("Traceback (most recent call last):")
    assert (s.start, s.bold) == (0, True)
    assert list(TracebackRule().spans("normal line")) == []
    (s,) = JsonKeyRule().spans('{"key": 1}')
    assert (s.start, s.end) == (2, 5)  # group(1) excludes the quotes


def test_cmake_rule_priority():
    err = list(CMakeRule().spans("CMake Error at foo:1"))
    assert len(err) == 1 and err[0].bold is True
    status = list(CMakeRule().spans("-- Configuring done"))
    assert len(status) == 1 and status[0].end == len("-- Configuring done")
    build = list(CMakeRule().spans("[ 50%] Built target app"))
    assert len(build) == 1
    assert list(CMakeRule().spans("plain output")) == []


def test_just_rule():
    (s,) = JustRule().spans("# comment")
    assert s.italic is True
    (s,) = JustRule().spans("test: build")
    assert (s.start, s.end, s.bold) == (0, 4, True)
    (s,) = JustRule().spans('NAME := "x"')
    assert (s.start, s.end) == (0, 4)
    (s,) = JustRule().spans("echo {{NAME}}")
    assert s is not None
    assert list(JustRule().spans("plain words here")) == []


def test_url_and_file_rules():
    (s,) = UrlRule().spans("see https://example.com now")
    assert s.anchor_href == "https://example.com"
    assert s.underline is True
    (s,) = FileRule().spans('File "src/main.py:10" bad')
    assert s.anchor_href == "src/main.py"
    assert list(FileRule().spans("https://example.com/x")) == []


def test_custom_rule_end_to_end(viewer):
    class BangRule:
        def spans(self, text):
            i = text.find("!")
            if i >= 0:
                yield Span(i, i + 1, bold=True)

    viewer.setAnsiText("hey!\n")
    viewer.add_highlight_rule(BangRule())
    try:
        viewer.appendAnsiText("wow!\n")
        block = viewer.document().findBlockByNumber(1)
        cur = QTextCursor(viewer.document())
        cur.setPosition(block.position() + 3)
        cur.setPosition(block.position() + 4, QTextCursor.MoveMode.KeepAnchor)
        assert cur.charFormat().fontWeight() >= 600
    finally:
        viewer.remove_highlight_rule(viewer.highlight_rules()[0])
    assert viewer.highlight_rules() == []
