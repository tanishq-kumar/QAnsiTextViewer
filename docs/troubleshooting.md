---
hide:
  - navigation
---

# Troubleshooting

## Why was my input ignored?

Contract violations raise (`TypeError`/`ValueError` naming the offender).
Degraded-but-safe fallbacks — rejected regex, clamped limits, trimmed
pause buffers, dropped async chunks, skipped mega-lines — log at DEBUG on
the `ansi_text_viewer` logger instead of failing:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("ansi_text_viewer").setLevel(logging.DEBUG)
```

## Invisible text

Unstyled text follows the theme (black on white in light mode,
light-on-dark in dark mode). If everything looks blank, something forced
a mismatched pair — check `viewer.defaultColors()` and re-enable
`setColorsFollowTheme(True)`, or pick explicit colors with
`setDefaultColors()`.

## `QFontDatabase: Cannot find font directory`

Harmless headless-environment noise (PySide ships no fonts). The viewer
falls back to a monospace hint automatically; install a system monospace
font (e.g. DejaVu) to silence it.

## GUI tests fail without a display

The suite drives real widgets. Headless runners must set:

```bash
QT_QPA_PLATFORM=offscreen
```

`tests/conftest.py` already does this; plain `just test` needs nothing
extra. Debian/Ubuntu CI also needs the Qt runtime libs from
`.github/workflows/ci.yml` (`libgl1`, `libegl1`, `libxkbcommon0`,
`libdbus-1-3`, `libfontconfig1`).

## Cleared text reappears

Pending async chunks resurrect cleared output. Call
`cancelAsyncAppends()` first — or rely on `clear()`, which already drops
the queue.

## Bookmarks jump nowhere

Navigation skips filtered-out lines on purpose. `gotoNextBookmark()`
returns `-1` when every bookmark is hidden; clear the filter to reach them.
Bookmarks live on their text blocks, so trimming or clearing the document
drops them for good — sessions only restore survivors.
