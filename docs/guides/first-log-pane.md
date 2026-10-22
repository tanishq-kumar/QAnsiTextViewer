# Your first log pane

The [quick start](../index.md#quick-start) shows the widget on its own. A
real app puts it in a window next to a search box. This guide builds that
window step by step: viewer, search field, match counter, and a filter that
hides lines that don't match.

## The window

`AnsiTextViewer` is a regular `QWidget`, so it goes into any layout:

```python title="log_window.py" linenums="1"
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QVBoxLayout, QWidget,
)
from ansi_text_viewer import AnsiTextViewer


class LogWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.total = self.current = 0  # match counter state
        self.viewer = AnsiTextViewer()
        self.viewer.setLogLevelHighlighting(True)

        self.search = QLineEdit(placeholderText="Search (Ctrl+F)")
        self.count = QLabel("0/0")
        self.filter = QLineEdit(placeholderText="Filter lines...")

        bar = QHBoxLayout()
        bar.addWidget(self.search)
        bar.addWidget(self.count)
        bar.addWidget(self.filter)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.viewer)
        layout.addLayout(bar)
        self.setCentralWidget(root)


app = QApplication([])
window = LogWindow()
window.viewer.appendAnsiText(
    "\x1b[32m[INFO]\x1b[0m server up\n"
    "\x1b[33m[WARN]\x1b[0m retrying connection\n"
    "\x1b[31m[ERROR]\x1b[0m timeout after 30s\n"
)
window.show()
app.exec()
```

This already runs. The next two steps add code to it; each listing's header
says where the lines go.

## Wire up search

`highlight_search()` highlights every match, jumps to the first one, and
returns the count. The counter also has to follow ++f3++ and ++shift+f3++:
the viewer emits `nextRequested` / `prevRequested` just *before* it moves,
and wraps around at the ends, so the counter mirrors that.

Connect the signals at the end of `__init__`:

```python title="log_window.py · end of __init__"
        self.search.textChanged.connect(self.run_search)
        self.viewer.findRequested.connect(self.focus_search)
        self.viewer.nextRequested.connect(lambda: self.step(+1))
        self.viewer.prevRequested.connect(lambda: self.step(-1))
```

Then add these methods to `LogWindow`:

```python title="log_window.py · new methods in LogWindow"
    def run_search(self, text):
        self.total = self.viewer.highlight_search(text)
        self.current = 1 if self.total else 0
        self.update_count()

    def step(self, delta):
        # Runs just before the viewer moves; wrap the same way it does.
        if self.total:
            self.current = (self.current - 1 + delta) % self.total + 1
        self.update_count()

    def update_count(self):
        self.count.setText(f"{self.current}/{self.total}")

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()
```

The shortcuts are built in: ++ctrl+f++ emits `findRequested`, ++f3++ and
++shift+f3++ emit `nextRequested` / `prevRequested` and then move between
matches, and ++esc++ clears the highlight. They are application-wide, so
++f3++ still works while the search box has focus.

!!! tip "Your own buttons"
    Buttons don't need the signals. Call the methods and use their return
    values: `next_match()` and `prev_match()` return the 1-based index of
    the match that is now active.

## Wire up the filter

`filter_search()` hides every line that doesn't match. An empty query shows
everything again, and new lines are filtered as they arrive, so a live
stream respects the filter. One more line at the end of `__init__`:

```python title="log_window.py · end of __init__"
        self.filter.textChanged.connect(self.viewer.filter_search)
```

Both `highlight_search()` and `filter_search()` accept `use_regex=True` and
`match_case=True`. Invalid regex falls back to a literal search instead of
raising, and patterns over 500 characters are rejected, so you can pass user
input straight through.

## The whole file

??? example "log_window.py, assembled"

    ```python title="log_window.py" linenums="1"
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
        QVBoxLayout, QWidget,
    )
    from ansi_text_viewer import AnsiTextViewer


    class LogWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.total = self.current = 0  # match counter state
            self.viewer = AnsiTextViewer()
            self.viewer.setLogLevelHighlighting(True)

            self.search = QLineEdit(placeholderText="Search (Ctrl+F)")
            self.count = QLabel("0/0")
            self.filter = QLineEdit(placeholderText="Filter lines...")

            bar = QHBoxLayout()
            bar.addWidget(self.search)
            bar.addWidget(self.count)
            bar.addWidget(self.filter)

            root = QWidget()
            layout = QVBoxLayout(root)
            layout.addWidget(self.viewer)
            layout.addLayout(bar)
            self.setCentralWidget(root)

            self.search.textChanged.connect(self.run_search)
            self.viewer.findRequested.connect(self.focus_search)
            self.viewer.nextRequested.connect(lambda: self.step(+1))
            self.viewer.prevRequested.connect(lambda: self.step(-1))
            self.filter.textChanged.connect(self.viewer.filter_search)

        def run_search(self, text):
            self.total = self.viewer.highlight_search(text)
            self.current = 1 if self.total else 0
            self.update_count()

        def step(self, delta):
            # Runs just before the viewer moves; wrap the same way it does.
            if self.total:
                self.current = (self.current - 1 + delta) % self.total + 1
            self.update_count()

        def update_count(self):
            self.count.setText(f"{self.current}/{self.total}")

        def focus_search(self):
            self.search.setFocus()
            self.search.selectAll()


    app = QApplication([])
    window = LogWindow()
    window.viewer.appendAnsiText(
        "\x1b[32m[INFO]\x1b[0m server up\n"
        "\x1b[33m[WARN]\x1b[0m retrying connection\n"
        "\x1b[31m[ERROR]\x1b[0m timeout after 30s\n"
    )
    window.show()
    app.exec()
    ```

<figure class="gb-figure gb-hero" markdown>
![The finished log window: three colored log lines, the search box holding "timeout" with the match highlighted, the counter reading 1/1, and an empty filter box](../assets/guide_log_window.png#only-light){ width="640" }
![The finished log window: three colored log lines, the search box holding "timeout" with the match highlighted, the counter reading 1/1, and an empty filter box](../assets/guide_log_window_dark.png#only-dark){ width="640" }
<figcaption>The assembled file, run as is, after typing <code>timeout</code> into the search box.</figcaption>
</figure>

## Next steps

- Feed it real output: [Streaming process output](streaming.md).
- Match your app's look: [Themes and colors](theming.md).
- Bookmarks, sessions, and export: [Viewer API](../api/viewer.md#bookmarks).
