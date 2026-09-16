# Changelog

All notable changes to this project are documented here, newest first.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-09-17

### Added

- Async non-blocking appends (`appendAnsiTextAsync`, progress/finished
  signals, cancel) with byte-identical output to the sync path.
- Pluggable highlight rules (`HighlightRule` protocol, `Span`,
  `add_highlight_rule`) covering log levels, tracebacks, JSON, CMake,
  justfiles, URLs, and `file:line` links.
- Theme-following default text colors with manual override
  (`setDefaultColors`, `setColorsFollowTheme`) and session persistence.
- Font controls (`setFontSize`, `setFontFamily`, `useSystemFont`).
- Strict boolean parsing (`"false"`/`"0"`/`"off"` work) and symmetric
  `is...()` getters for every flag.
- Bookmarks stored on text blocks; gutter click, list panel, navigation
  skips filtered-out lines.
- Sessions (JSON save/load with validation), export (txt/html/md),
  selection stats, current-line highlight, max-blocks/line-length caps.
- Color knobs (`setLogLevelColors`, `setBookmarkColor`,
  `setSearchHighlightColor` active color, `currentLineColor`).
- Debug diagnostics: every silent fallback logs on the `ansi_text_viewer`
  logger; contract violations raise with the offender named.
- Tooling: pytest suite, ruff (Google docstrings), mypy + ty, MkDocs API
  docs with gallery, SHA-pinned CI on Python 3.11–3.14, commitizen with
  conventional commits and Pages deploy workflow.
- Packaging: PyPI metadata (license, classifiers, authors, URLs),
  `py.typed` marker verified in the wheel via `twine check`.

### Changed

- Default text colors now follow the theme instead of fixed
  terminal white-on-black.
- Links open on ++ctrl+click++ only (was: single click).
- Python requirement lowered to `>=3.11`.

### Removed

- `test.py` demo shim — import the demo from `demo` instead:
  `from demo import TestWindow`.
