"""Tests for theme-following default colors and manual overrides."""

from PySide6.QtGui import QColor, QTextCursor


def _char_format(viewer, block_no=0, pos=0):
    block = viewer.document().findBlockByNumber(block_no)
    cur = QTextCursor(viewer.document())
    cur.setPosition(block.position() + pos)
    cur.setPosition(block.position() + pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return cur.charFormat()


def test_handler_default_colors_api():
    from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler

    h = AnsiEscapeHandler()
    assert h.defaultColors() == ((255, 255, 255), (0, 0, 0))
    h.setDefaultColors((1, 2, 3), (4, 5, 6))
    assert h.defaultColors() == ((1, 2, 3), (4, 5, 6))
    h.reset()
    assert h.defaultColors() == ((1, 2, 3), (4, 5, 6))
    actions = h.parse("x")
    assert actions[0][2].fg == (1, 2, 3)


def test_light_theme_uses_dark_text(viewer):
    viewer.setTheme("light")
    viewer.setAnsiText("hello\n")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().lightness() < 128
    assert fmt.background().color().lightness() > 128


def test_dark_theme_uses_light_text(viewer):
    viewer.setTheme("dark")
    viewer.setAnsiText("hello\n")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().lightness() > 128
    assert fmt.background().color().lightness() < 128
    viewer.setTheme("light")


def test_explicit_sgr_survives_theme(viewer):
    viewer.setTheme("light")
    viewer.setAnsiText("\x1b[31mred\x1b[0m\n")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().red() == 170


def test_manual_override_disables_follow(viewer):
    assert viewer.colorsFollowTheme() is True
    viewer.setDefaultColors(QColor(10, 20, 30), QColor(40, 50, 60))
    assert viewer.colorsFollowTheme() is False
    viewer.setAnsiText("hi\n")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().red() == 10
    viewer.setTheme("dark")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().red() == 10
    viewer.setColorsFollowTheme(True)
    assert viewer.colorsFollowTheme() is True
    viewer.setAnsiText("hi\n")
    fmt = _char_format(viewer)
    assert fmt.foreground().color().red() == 212


def test_session_preserves_appearance(viewer, tmp_path):
    viewer.setTheme("dark")
    viewer.setDefaultColors(QColor(1, 2, 3), QColor(4, 5, 6))
    path = tmp_path / "look.json"
    viewer.saveSession(str(path))
    viewer.setTheme("light")
    viewer.setColorsFollowTheme(True)
    viewer.loadSession(str(path))
    assert viewer.theme() == "dark"
    assert viewer.colorsFollowTheme() is False
    fg, bg = viewer.defaultColors()
    assert (fg.red(), fg.green(), fg.blue()) == (1, 2, 3)
    assert (bg.red(), bg.green(), bg.blue()) == (4, 5, 6)
