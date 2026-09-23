from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler


def test_plain_text_single_action(handler):
    actions = handler.parse("hello")
    assert len(actions) == 1
    assert actions[0][0] == "text"
    assert actions[0][1] == "hello"


def test_empty_string(handler):
    assert handler.parse("") == []


def test_bold_and_reset():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[1mBold\x1b[0mPlain")
    assert actions[0][0] == "text"
    assert actions[0][1] == "Bold"
    assert actions[0][2].bold is True
    assert actions[1][1] == "Plain"


def test_fg_standard_color():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[31mred")
    assert actions[0][2].fg == (170, 0, 0)


def test_bg_standard_color():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[42mgreen-bg")
    assert actions[0][2].bg == (0, 170, 0)


def test_bright_fg():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[91mbright")
    # bright red = 170+85, 0+85, 0+85
    assert actions[0][2].fg == (255, 85, 85)


def test_256_color():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[38;5;196mred256")
    assert actions[0][2].fg == (255, 0, 0)


def test_truecolor():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[38;2;255;165;0morange")
    assert actions[0][2].fg == (255, 165, 0)


def test_cursor_movements():
    h = AnsiEscapeHandler()
    assert h.parse("\x1b[A") == [("cursor_up", 1)]
    assert h.parse("\x1b[3B") == [("cursor_down", 3)]
    assert h.parse("\x1b[2C") == [("cursor_forward", 2)]
    assert h.parse("\x1b[D") == [("cursor_back", 1)]
    assert h.parse("\x1b[5G") == [("cursor_col", 5)]
    assert h.parse("\x1b[2;10H") == [("cursor_pos", 2, 10)]


def test_erase_actions():
    h = AnsiEscapeHandler()
    assert h.parse("\x1b[2J") == [("erase_screen", 2)]
    assert h.parse("\x1b[K") == [("erase_line", 0)]
    assert h.parse("\x1b[2K") == [("erase_line", 2)]


def test_hide_show_cursor():
    h = AnsiEscapeHandler()
    assert h.parse("\x1b[?25l") == [("hide_cursor",)]
    assert h.parse("\x1b[?25h") == [("show_cursor",)]


def test_bare_sgr_reset():
    h = AnsiEscapeHandler()
    h.parse("\x1b[1m")  # bold on
    assert h.bold is True
    h.parse("\x1b[m")  # bare reset
    assert h.bold is False


def test_state_persists_until_reset():
    h = AnsiEscapeHandler()
    h.parse("\x1b[31m")
    a1 = h.parse("a")[0][2].fg
    a2 = h.parse("b")[0][2].fg
    assert a1 == a2 == (170, 0, 0)
    h.reset()
    a3 = h.parse("c")[0][2].fg
    assert a3 == (255, 255, 255)


def test_italic_underline_strike():
    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[3;4;9mstyled")
    style = actions[0][2]
    assert style.italic is True
    assert style.underline is True
    assert style.strikethrough is True
