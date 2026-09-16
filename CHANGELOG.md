# Changelog

All notable changes to this project are documented here, newest first.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
- Tooling: pytest suite, ruff (Google docstrings), mypy + ty, MkDocs API
  docs, SHA-pinned CI on Python 3.11–3.14.

### Changed

- Default text colors now follow the theme instead of fixed
  terminal white-on-black.
- Links open on ++ctrl+click++ only (was: single click).
- Python requirement lowered to `>=3.11`.

### Removed

- `test.py` demo shim — import the demo from `demo` instead:
  `from demo import TestWindow`.
