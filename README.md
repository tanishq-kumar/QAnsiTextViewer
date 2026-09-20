# QAnsiTextViewer

![CI](https://github.com/tanishq-kumar/QAnsiTextViewer/actions/workflows/ci.yml/badge.svg) [![Docs](https://img.shields.io/badge/docs-live-blue)](https://tanishq-kumar.github.io/QAnsiTextViewer/) [![PyPI](https://img.shields.io/pypi/v/qansitextviewer)](https://pypi.org/project/qansitextviewer/)

ANSI Text Viewer - Qt log-viewer widget for Python

Drop-in `QWidget` that renders ANSI escape codes and colored terminal output:
tail logs, search and filter them, bookmark lines, and save sessions.
Works with both **PySide6** (tested) and **PyQt** (same Qt API, no code changes).

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

## FAQ

<details>
<summary><strong>PySide6 or PyQt?</strong></summary>

PySide6 is the tested dependency. PyQt exposes the same `QWidget` API,
so the viewer works there too — report any gap as a bug.
</details>

<details>
<summary><strong>Why not <code>QPlainTextEdit</code> + manual parsing?</strong></summary>

That's exactly the boilerplate this widget removes: SGR/256-color/truecolor
parsing, `\r` progress lines, search, bookmarks, themes, and session save/load
in one typed widget.
</details>

<details>
<summary><strong>How is this different from a terminal emulator?</strong></summary>

Terminal emulators run interactive shells. This is a read-oriented log viewer:
append-only text, regex search/filter, bookmarks, and export to `.txt`/`.html`/`.md`.
</details>
