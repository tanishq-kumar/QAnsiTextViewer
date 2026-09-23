"""Decode ANSI escape sequences into text and cursor actions.

Deliberately free of Qt: the parser emits plain data (see `TextStyle`) so it
can run anywhere — tests, fuzzers, other runtimes. The widget converts styles
to ``QTextCharFormat`` at the boundary (``_style_to_format``).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextStyle:
    """Effective style of a ``("text", ...)`` action payload.

    Colors are ``(r, g, b)`` tuples with dimming and reverse-video already
    applied, mirroring what the widget used to bake into ``QTextCharFormat``.
    """

    fg: tuple[int, int, int]
    bg: tuple[int, int, int]
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False


_DEFAULT_FG = (255, 255, 255)
_DEFAULT_BG = (0, 0, 0)


class AnsiEscapeHandler:
    r"""Stateful ANSI SGR and cursor-sequence decoder.

    Keeps the current style (colors, bold, ...) across `parse` calls,
    like a terminal. Repeat counts are clamped to blunt DoS input.

    Examples:
        >>> handler = AnsiEscapeHandler()
        >>> actions = handler.parse("\x1b[1mbold")
        >>> actions[0][0]
        'text'
    """

    def __init__(self):
        """Create a handler with default terminal styling."""
        self._custom_8: dict[tuple[int, bool], tuple[int, int, int]] = {}
        self.default_fg = _DEFAULT_FG
        self.default_bg = _DEFAULT_BG
        self.reset()

    def reset(self):
        """Restore default colors and clear all text attributes."""
        self.fg = self.default_fg
        self.bg = self.default_bg
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
        self.blink = False
        self.reverse = False
        self.strikethrough = False

    def parse(self, text: str) -> list[tuple]:
        r"""Parse text with escape sequences into display actions.

        Args:
            text: Raw text that may contain ``ESC[`` sequences.

        Returns:
            List of ``("text", str, TextStyle)`` tuples plus cursor
            actions such as ``("cursor_up", n)`` or ``("erase_line", mode)``.

        Examples:
            >>> handler = AnsiEscapeHandler()
            >>> actions = handler.parse("plain")
            >>> actions[0][:2]
            ('text', 'plain')
        """
        actions: list[tuple] = []
        i = 0
        n = len(text)

        while i < n:
            if text[i] != "\x1b":
                start = i
                while i < n and text[i] != "\x1b":
                    i += 1
                actions.append(("text", text[start:i], self.__get_format()))
                continue

            # \x1b[ ...
            if i + 1 < n and text[i + 1] == "[":
                i += 2

                question_mark = False
                if i < n and text[i] == "?":
                    question_mark = True
                    i += 1

                params = []
                num = ""

                def _num(n: str) -> int:
                    # Clamp huge repeat counts (e.g. \x1b[999999999C) to avoid
                    # cursor-movement DoS loops downstream.
                    try:
                        return min(int(n), 10000) if n else 0
                    except ValueError:
                        return 0

                while i < n:
                    c = text[i]
                    if c.isdigit():
                        # Cap digit run early so 1MB of digits can't build a giant int.
                        if len(num) < 5:
                            num += c
                        elif len(num) == 5:
                            num = "10000"
                    elif c == ";":
                        params.append(_num(num))
                        num = ""
                    else:
                        if num:
                            params.append(_num(num))

                        if c == "m":
                            if not params and not num:  # e.g., \x1b[m
                                self.__apply_sgr([])
                            else:
                                self.__apply_sgr(params)
                        elif c == "A":
                            actions.append(("cursor_up", params[0] if params else 1))
                        elif c == "B":
                            actions.append(("cursor_down", params[0] if params else 1))
                        elif c == "C":
                            actions.append(
                                ("cursor_forward", params[0] if params else 1)
                            )
                        elif c == "D":
                            actions.append(("cursor_back", params[0] if params else 1))
                        elif c == "G":
                            actions.append(("cursor_col", params[0] if params else 1))
                        elif c == "H" or c == "f":
                            row = params[0] if len(params) > 0 else 1
                            col = params[1] if len(params) > 1 else 1
                            actions.append(("cursor_pos", row, col))
                        elif c == "J":
                            actions.append(("erase_screen", params[0] if params else 0))
                        elif c == "K":
                            actions.append(("erase_line", params[0] if params else 0))
                        elif c == "h" and question_mark:
                            if params and params[0] == 25:
                                actions.append(("show_cursor",))
                        elif c == "l" and question_mark:
                            if params and params[0] == 25:
                                actions.append(("hide_cursor",))

                        i += 1
                        break
                    i += 1
                continue

            i += 1

        return actions

    def __get_format(self) -> TextStyle:
        fg = self.fg
        bg = self.bg

        if self.dim:
            fg = (max(0, fg[0] // 2), max(0, fg[1] // 2), max(0, fg[2] // 2))

        if self.reverse:
            fg, bg = bg, fg

        return TextStyle(
            fg=fg,
            bg=bg,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
        )

    def __apply_sgr(self, params: list):
        if not params:
            self.reset()
            return

        i = 0
        while i < len(params):
            code = params[i]
            i += 1

            if code == 0:
                self.reset()
            elif code == 1:
                self.bold = True
            elif code == 2:
                self.dim = True
            elif code == 3:
                self.italic = True
            elif code == 4:
                self.underline = True
            elif code == 5:
                self.blink = True
            elif code == 7:
                self.reverse = True
            elif code == 9:
                self.strikethrough = True
            elif code == 22:
                self.bold = False
                self.dim = False
            elif code == 23:
                self.italic = False
            elif code == 24:
                self.underline = False
            elif code == 25:
                self.blink = False
            elif code == 27:
                self.reverse = False
            elif code == 29:
                self.strikethrough = False

            # Standard colors
            elif 30 <= code <= 37:
                self.fg = self.__ansi8_color(code - 30)
            elif 40 <= code <= 47:
                self.bg = self.__ansi8_color(code - 40)
            elif 90 <= code <= 97:
                self.fg = self.__ansi8_color(code - 90, bright=True)
            elif 100 <= code <= 107:
                self.bg = self.__ansi8_color(code - 100, bright=True)

            # 256 colors
            elif code == 38 and i < len(params) and params[i] == 5:
                i += 2
                if i - 1 < len(params):
                    self.fg = self.__color_256(params[i - 1])
            elif code == 48 and i < len(params) and params[i] == 5:
                i += 2
                if i - 1 < len(params):
                    self.bg = self.__color_256(params[i - 1])

            # Truecolor RGB
            elif code == 38 and i + 3 < len(params) and params[i] == 2:
                i += 4
                r, g, b = params[i - 3 : i]
                self.fg = (r, g, b)
            elif code == 48 and i + 3 < len(params) and params[i] == 2:
                i += 4
                r, g, b = params[i - 3 : i]
                self.bg = (r, g, b)

    def setDefaultColors(
        self,
        fg: tuple[int, int, int] | None = None,
        bg: tuple[int, int, int] | None = None,
    ):
        """Override the colors used by SGR reset.

        Args:
            fg: Default foreground ``(r, g, b)``, or None to keep it.
            bg: Default background ``(r, g, b)``, or None to keep it.

        Examples:
            >>> handler.setDefaultColors((0, 0, 0), (255, 255, 255))
        """
        if fg is not None:
            self.default_fg = fg
        if bg is not None:
            self.default_bg = bg
        self.reset()

    def defaultColors(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Return the current ``(foreground, background)`` defaults."""
        return (self.default_fg, self.default_bg)

    def setAnsi8Color(
        self, idx: int, color: tuple[int, int, int], bright: bool = False
    ):
        """Override one ANSI base color.

        Args:
            idx: Base color 0..7.
            color: Replacement ``(r, g, b)`` color.
            bright: Whether it applies to the bright variant.
        """
        self._custom_8[(idx % 8, bool(bright))] = color

    def resetPalette(self):
        """Drop all custom palette overrides."""
        self._custom_8.clear()

    def palette(self) -> dict:
        """Return custom ``(index, bright) -> (r, g, b)`` overrides."""
        return dict(self._custom_8)

    def __ansi8_color(self, idx: int, bright: bool = False):
        key = (idx % 8, bool(bright))
        if key in self._custom_8:
            return self._custom_8[key]
        palette = [
            (0, 0, 0),
            (170, 0, 0),
            (0, 170, 0),
            (170, 170, 0),
            (0, 0, 170),
            (170, 0, 170),
            (0, 170, 170),
            (170, 170, 170),
        ]
        r, g, b = palette[idx % 8]
        if bright:
            r, g, b = min(r + 85, 255), min(g + 85, 255), min(b + 85, 255)
        return (r, g, b)

    def __color_256(self, idx: int):
        if idx < 16:
            return self.__ansi8_color(idx % 8, bright=idx >= 8)

        if idx < 232:  # 6x6x6 cube
            idx -= 16
            return ((idx // 36) * 51, ((idx // 6) % 6) * 51, (idx % 6) * 51)

        # Grayscale
        gray = 8 + (idx - 232) * 10
        return (gray, gray, gray)
