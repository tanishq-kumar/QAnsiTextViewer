# Internals

The pieces the viewer composes. You rarely need these directly, but they
are public, typed, and tested on their own.

## ANSI decoding

`AnsiEscapeHandler` keeps terminal style state (colors, bold, italic,
reverse, …) across `parse()` calls, exactly like a terminal: a `\x1b[31m`
on one append still colors the next append until `\x1b[0m` resets it.
Repeat counts are clamped at 10,000 and digit runs capped, so hostile
input like `\x1b[999999999C` cannot freeze the UI. `setDefaultColors()`
changes what reset restores (this is how themes work); `setAnsi8Color()`
overrides individual palette entries.

## Search engine

`SearchHandler` implements highlight search over the `QTextDocument`
(plain or `QRegularExpression`, optional case sensitivity) with wrapping
`next_match()` / `prev_match()` navigation, plus the
hide-non-matching-blocks filter. Defenses: invalid regex falls back to a
literal search instead of raising, and patterns over 500 characters are
rejected to blunt ReDoS. Newly appended blocks are filtered on arrival via
`update_new_blocks()`, so live streams respect an active filter.

## Gutter

`LineNumberArea` paints line numbers, bookmark markers, and theme-aware
gutter colors delegated from the viewer. Clicking it toggles the bookmark
on that line (`toggleBookmarkAtY()` refuses invisible blocks).

::: ansi_text_viewer.ansi_escape_handler.AnsiEscapeHandler
    options:
      show_root_heading: true
      members: true

::: ansi_text_viewer.search_handler.SearchHandler
    options:
      show_root_heading: true
      members: true

::: ansi_text_viewer.line_number_area.LineNumberArea
    options:
      show_root_heading: true
      members: true
