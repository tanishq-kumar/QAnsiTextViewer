# Viewer

The main widget. One import, one class, sensible defaults — everything
works with zero configuration and every behavior has a setter/getter pair.

```python
from ansi_text_viewer import AnsiTextViewer

viewer = AnsiTextViewer()
viewer.appendAnsiText("\x1b[32m[INFO]\x1b[0m server up\n")
```

| Feature | What lives here |
| ------- | --------------- |
| [Appending](#appending-content) | Write, replace, clear, pause, clear-on-start |
| [Non-blocking bursts](#non-blocking-bursts) | Async queue, progress, cancel |
| [Search & filter](#search-filter) | Highlight, navigate, hide lines |
| [Limits](#limits-and-performance) | Memory caps |
| [Fonts & zoom](#fonts-zoom) | Families, sizes, system font |
| [Layout](#layout-scroll-and-gutter) | Wrap, scroll, line numbers |
| [Highlight toggles](#timestamps-and-highlight-toggles) | Timestamp, levels, syntax, custom rules |
| [Current line](#current-line) | Cursor-line highlight |
| [Links](#links) | Clickable URLs and file paths |
| [Copy, export, sessions](#copy-export-sessions) | Clipboard, files, stats |
| [Bookmarks](#bookmarks) | Mark, navigate, persist |
| [Theme & colors](#theme-colors) | Light/dark/auto, palettes, defaults |

## Shortcuts

| Keys | Action |
| ---- | ------ |
| ++ctrl+f++ | Focus search (`findRequested`) |
| ++f3++ / ++shift+f3++ | Next / previous match |
| ++esc++ | Clear search highlight |
| ++ctrl++ + wheel | Zoom in / out |

Shortcuts are application-wide, so ++f3++ works while typing in a search
box.

## Signals

The widget talks back through Qt signals — no polling needed:

| Signal | Emitted when |
| ------ | ------------ |
| `bookmarksChanged(list)` | Any bookmark is added, removed, or cleared (payload: block numbers) |
| `findRequested()` | ++ctrl+f++ is pressed — focus your search field |
| `nextRequested()` / `prevRequested()` | ++f3++ / ++shift+f3++ is pressed |
| `asyncAppendProgress(int, int)` | Each async chunk lands (`done`, `total` lines) |
| `asyncAppendFinished()` | The async queue drains |

```python
viewer.bookmarksChanged.connect(refresh_bookmark_list)
viewer.findRequested.connect(search_box.setFocus)
```

## Appending content

`appendAnsiText()` parses ANSI SGR colors, 256-color and truecolor codes,
plus cursor movement and erase sequences. A carriage return overwrites the
current line instead of appending, so progress bars render in place:

```python
viewer.appendAnsiText("Downloading... 10%\rDownloading... 100%\n")
```

`setAnsiText()` replaces everything, `insertAnsiText()` writes at the
cursor, and `clear()` resets text, ANSI state, search, bookmarks and any
queued async chunks. `pause_stream()` buffers incoming text (capped at
5000 entries) until `resume_stream()` flushes it. Pair
`setClearOnStart(True)` with `beginNewStream()` to wipe the view whenever
a new stream starts.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.appendAnsiText
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setAnsiText
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.insertAnsiText
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.clear
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.pause_stream
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.resume_stream
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.beginNewStream
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setClearOnStart
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isClearOnStart

## Non-blocking bursts

`appendAnsiTextAsync()` splits text into line chunks inserted one per
event-loop turn, so a 100k-line burst never freezes the UI. Chunking
reuses the exact sync path — ANSI state, `\r` handling, timestamps and
highlighting are byte-identical (covered by `test_async_matches_sync`).
Call it on the GUI thread; from worker threads, connect a signal to it —
Qt queues the call across threads automatically.

```python
viewer.appendAnsiTextAsync(huge_log, chunk_lines=500)
viewer.asyncAppendProgress.connect(
    lambda done, total: bar.setValue(100 * done // total)
)
viewer.asyncAppendFinished.connect(lambda: status.showMessage("done"))
```

`hasPendingAppends()` reports queued work and `cancelAsyncAppends()`
drops it (the in-flight chunk still finishes). `clear()` also drops the
queue, so cleared output can never be resurrected by pending chunks.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.appendAnsiTextAsync
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.hasPendingAppends
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.cancelAsyncAppends

## Search & filter

`highlight_search()` highlights every match and jumps to the first,
returning the count. Over-long patterns are rejected to blunt ReDoS, and
invalid regex falls back safely instead of raising:

```python
n = viewer.highlight_search(r"ERR-\d+", use_regex=True)
viewer.next_match()   # F3
viewer.prev_match()   # Shift+F3
```

`filter_search()` hides non-matching blocks (line numbers and bookmarks
track the survivors); an empty query restores everything. Newly appended
lines are filtered on arrival, and match colors are tunable with
`setSearchHighlightColor()`.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.highlight_search
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.next_match
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.prev_match
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.clear_search_highlight
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.filter_search
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setSearchHighlightColor
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.searchHighlightColors

## Limits and performance

Two caps bound steady-state memory: `setMaximumBlocks()` (default 10,000
lines, oldest trimmed) and `setMaxLineLength()` (default 10,000 chars per
line, truncated with a marker). Measured on this machine: 10k plain lines
add ~6MB over Qt's ~4MB baseline; a 2MB single line would spike ~70MB of
per-character overhead, hence the truncation. Bulk appends freeze widget
updates and refresh once, and bookmark scans are skipped entirely when no
bookmarks exist — 2000 streaming lines land in ~0.5s. Dense URL anchors
are the one known cost (~4KB/line); turn links off for firehose logs.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setMaximumBlocks
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.maximumBlocks
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setMaxLineLength
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.maxLineLength

## Fonts & zoom

Fonts default to the system fixed font at 10pt and ignore later
application-font changes (frozen for layout stability). `setFontSize()`
doubles as the zoom-reset size, `setFontFamily()` keeps the size, and
`useSystemFont()` takes a one-shot snapshot of `QApplication.font()`.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setMonospaceFont
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setFontSize
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setFontFamily
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.useSystemFont
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.resetZoom
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.wheelEvent

## Layout, scroll and gutter

Word wrap is off by default (logs scroll sideways); auto-scroll pins the
bottom on new output; the gutter shows line numbers with bookmark ticks.
The `lineNumberArea*` methods and `resizeEvent` are Qt plumbing most apps
never call directly — listed here for completeness.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setWordWrapEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isWordWrapEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setAutoScroll
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isAutoScroll
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setLineNumbersVisible
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isLineNumbersVisible
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.lineNumberAreaWidth
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.updateLineNumberAreaWidth
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.updateLineNumberArea
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.resizeEvent
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.lineNumberAreaPaintEvent

## Timestamps and highlight toggles

`setTimestampEnabled()` prefixes new lines with the current time.
`setLogLevelHighlighting()` colors `[ERROR]`/`[WARN]`/`[INFO]`/`[DEBUG]`
markers; `setSyntaxHighlighting()` covers tracebacks, JSON keys, CMake and
justfiles (see [Highlighting](highlighting.md)). Custom languages plug in
through `add_highlight_rule()` without touching the viewer.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setTimestampEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isTimestampEnabled
Colors are injectable: `setLogLevelColors()` replaces the level map used
for future highlights (read back with `logLevelColors()`).

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setLogLevelHighlighting
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isLogLevelHighlighting
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setLogLevelColors
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.logLevelColors
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setSyntaxHighlighting
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isSyntaxHighlighting
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.add_highlight_rule
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.remove_highlight_rule
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.highlight_rules

## Current line

Highlights the cursor line, merged with — never replacing — search and
bookmark highlights. `setExtraSelections()` is the interception point the
search engine writes through; `searchExtraSelections()` reads back just
the search part.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setCurrentLineHighlightEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isCurrentLineHighlightEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.currentLineColor
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setExtraSelections
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.searchExtraSelections

## Links

`https://` URLs and `path/to/file.py:line` references become clickable
anchors, opened with ++ctrl++ + click (plain clicks just move the cursor —
single-click-open would let a hostile log line phish you). `mousePressEvent`
enforces the modifier, `mouseMoveEvent` shows the pointing hand, and
`contextMenuEvent` builds the right-click menu. Disable entirely with
`setLinksEnabled(False)` for untrusted logs.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setLinksEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isLinksEnabled
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.mousePressEvent
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.mouseMoveEvent
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.contextMenuEvent

## Copy, export, sessions

- `copySelectedPlainText()` and `copySelectedWithAnsi()` (SGR codes
  reconstructed from the actual formats).
- `exportToFile()` writes `.txt`, `.html`, or `.md` from the suffix.
- `saveSession()` / `loadSession()` persist text, bookmarks, and settings
  as JSON, with size and shape validation (10MB file / 5MB text caps).
- `selectionStats()` returns `chars`/`words`/`lines` for status bars.

```python
viewer.saveSession("run.json")
viewer.loadSession("run.json")
```

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.selectedPlainText
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.copySelectedPlainText
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.selectedTextWithAnsi
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.copySelectedWithAnsi
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.exportToFile
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.selectionStats
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.saveSession
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.loadSession

## Bookmarks

Bookmarks live on the text block itself, so trimming, filtering, or
clearing can never leave stale line numbers behind. Toggle via
`toggleBookmark()`, by clicking the gutter (`toggleBookmarkAtY()` refuses
invisible blocks), or from the context menu;
`gotoNextBookmark()` / `gotoPrevBookmark()` wrap around and skip
filtered-out lines. `bookmarkedLines()`, `bookmarkedPreviews()`, and the
`bookmarksChanged` signal feed list UIs like the demo's panel.

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.toggleBookmark
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.toggleBookmarkAtY
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.addBookmark
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.removeBookmark
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.isBookmarked
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.bookmarkedLines
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.bookmarkedPreviews
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.clearBookmarks
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.gotoNextBookmark
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.gotoPrevBookmark
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setBookmarkColor
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.bookmarkColor

## Theme & colors

`setTheme("light")`, `"dark"`, or `"auto"` (follows the OS and live-updates
on system changes). Unstyled text colors follow the theme — black on white
in light mode, `#d4d4d4` on `#1e1e1e` in dark — so plain logs always match
the background instead of showing terminal-white pills. Explicit SGR colors
are never touched.

```python
viewer.setTheme("auto")
viewer.setDefaultColors(QColor(0, 0, 0), QColor(255, 255, 255))  # manual
viewer.setColorsFollowTheme(True)  # back to automatic
```

::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setTheme
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.theme
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.themeRequested
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setDefaultColors
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.defaultColors
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setColorsFollowTheme
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.colorsFollowTheme
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.setAnsiPaletteColor
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.resetAnsiPalette
::: ansi_text_viewer.ansi_text_viewer.AnsiTextViewer.ansiPalette
