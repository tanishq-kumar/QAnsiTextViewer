# QAnsiTextViewer

![CI](https://github.com/tanishq-kumar/QAnsiTextViewer/actions/workflows/ci.yml/badge.svg) [![Docs](https://img.shields.io/badge/docs-live-blue)](https://tanishq-kumar.github.io/QAnsiTextViewer/) [![PyPI](https://img.shields.io/pypi/v/qansitextviewer)](https://pypi.org/project/qansitextviewer/)

ANSI Text Viewer - QT Widget

## Install

```bash
uv add qansitextviewer
# or from GitHub / local build:
uv add git+https://github.com/tanishq-kumar/QAnsiTextViewer
uv build && uv pip install dist/qansitextviewer-*.whl
# or clone + develop:
uv sync --group dev
```

Requires Python `>=3.11`, PySide6 `>=6.5.0`.

## Quick start

```python
from PySide6.QtWidgets import QApplication
from ansi_text_viewer import AnsiTextViewer

app = QApplication([])
viewer = AnsiTextViewer()
viewer.appendAnsiText("\x1b[31mred\x1b[0m plain\n")
viewer.highlight_search("red")  # F3 / Shift+F3 navigates, Esc clears
viewer.setTheme("dark")
viewer.show()
app.exec()
```

Full demo app: `just demo` (or `uv run python demo.py`).

## API cheatsheet

| Task               | Call                                                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Append / replace   | `appendAnsiText(s)`, `setAnsiText(s)` (`\r` = progress overwrite)                                                                                                                     |
| Non-blocking burst | `appendAnsiTextAsync(s)` + `asyncAppendProgress` / `asyncAppendFinished`, `cancelAsyncAppends()`                                                                                      |
| Search / filter    | `highlight_search(q, use_regex, match_case)`, `next_match()`, `prev_match()`, `filter_search(q, ...)`                                                                                 |
| Limits             | `setMaximumBlocks(10000)`, `setMaxLineLength(10000)` (`0` = off)                                                                                                                      |
| Look               | `setTheme("light"\|"dark"\|"auto")`, `setMonospaceFont()`, `setFontSize()`, `setFontFamily()`, `useSystemFont()`, `setWordWrapEnabled()`, `setCurrentLineHighlightEnabled()`          |
| Appearance         | Theme-following defaults; `setDefaultColors(fg, bg)`, `setColorsFollowTheme(bool)`, `setAnsiPaletteColor()`, `setLogLevelColors()`, `setBookmarkColor()`, `setSearchHighlightColor()` |
| Log helpers        | `setTimestampEnabled()`, `setLogLevelHighlighting()`, `setSyntaxHighlighting()`                                                                                                       |
| Custom highlight   | `add_highlight_rule(rule)` with `spans(text)` (`ansi_text_viewer.highlight`)                                                                                                          |
| Bookmarks          | `toggleBookmark()` (or gutter click), `gotoNextBookmark()`, `bookmarkedLines()`, `bookmarksChanged` signal                                                                            |
| Copy / export      | `copySelectedPlainText()`, `copySelectedWithAnsi()`, `exportToFile(path)` (.txt/.html/.md)                                                                                            |
| Sessions           | `saveSession("s.json")`, `loadSession("s.json")`                                                                                                                                      |
| Shortcuts          | `Ctrl+F` → `findRequested`, `F3`/`Shift+F3`, `Esc` (app-wide)                                                                                                                         |

## Dev Commands

`just test` · `just demo` · `just run` · `just lint` · `just typecheck` · `just docs-build` — see `justfile`.
