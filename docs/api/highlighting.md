# Highlighting

Syntax highlighting is data, not code: each rule is a pure function from
one line of text to style spans. Rules run in registration order and later
spans merge over earlier ones; link anchors additionally skip overlaps, so
a `file.py:10` inside a URL stays one link. Lines over 10,000 characters
skip highlighting entirely (mega-line guard).

Add a language without touching the viewer:

```python
from ansi_text_viewer.highlight import HighlightRule, Span

class TodoRule:
    def spans(self, text):
        i = text.find("TODO")
        if i >= 0:
            yield Span(i, i + 4, bold=True)

viewer.add_highlight_rule(TodoRule())
viewer.remove_highlight_rule(rule)  # symmetrical removal
```

## Built-in rules

- **`LogLevelRule`** — `[ERROR]` / `WARN:`-style markers in bold level
  colors. Colors are injected through the constructor, so custom palettes
  compose: `LogLevelRule({"ERROR": QColor(255, 0, 0)})`.
- **`TracebackRule`** — whole-line red bold for Python `Traceback` headers.
- **`JsonKeyRule`** — blue `"key":` names.
- **`CMakeRule`** — `CMake Error` (red) vs `Warning` (orange), `-- Configuring…`
  status lines in blue, `[ 50%] Built target` in green. Error wins over
  status on the same line.
- **`JustRule`** — `#` comments (gray italic), `recipe:` names (blue bold),
  `NAME :=` assignments (purple bold), `{{vars}}` (magenta). Comment lines
  suppress the other justfile patterns.
- **`UrlRule`** — `http(s)://` anchors, blue underlined.
- **`FileRule`** — `path/to/file.py:line` anchors; the `:line` suffix is
  stripped from the href so the OS opens the file. Skips anything containing
  `://` so URLs keep a single anchor.

A `Span` carries `start`/`end` offsets plus optional `foreground`, `bold`,
`italic`, `underline`, and `anchor_href`. Spans are frozen dataclasses, so
rules stay trivially unit-testable without a widget.

::: ansi_text_viewer.highlight.Span
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.HighlightRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.LogLevelRule
    options:
      show_root_heading: true
      members: true

::: ansi_text_viewer.highlight.TracebackRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.JsonKeyRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.CMakeRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.JustRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.UrlRule
    options:
      show_root_heading: true

::: ansi_text_viewer.highlight.FileRule
    options:
      show_root_heading: true
