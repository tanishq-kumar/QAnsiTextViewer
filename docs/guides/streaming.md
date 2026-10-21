# Streaming process output

Most log panes show the output of something that is still running: a build,
a test run, a device talking over serial. This guide connects a subprocess
to the viewer, then covers the three things that go wrong with live output:
huge bursts, pausing, and restarting.

## Tail a subprocess

`QProcess` delivers output in arbitrary byte chunks. Decode them with an
incremental decoder, so a UTF-8 character split across two chunks still
decodes cleanly, and append the text as it arrives:

```python title="tail_process.py" linenums="1"
import codecs
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
from ansi_text_viewer import AnsiTextViewer

app = QApplication([])
viewer = AnsiTextViewer()
decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

process = QProcess()
process.setProcessChannelMode(
    QProcess.ProcessChannelMode.MergedChannels
)
process.readyReadStandardOutput.connect(
    lambda: viewer.appendAnsiText(
        decoder.decode(process.readAllStandardOutput().data())
    )
)
process.start(sys.executable, ["-m", "pytest", "--color=yes"])

viewer.resize(900, 600)
viewer.show()
app.exec()
```

ANSI style state carries across `appendAnsiText()` calls, exactly like a
terminal: a `\x1b[31m` in one chunk still colors the next chunk until a
`\x1b[0m` resets it. Carriage returns overwrite the current line, so
progress bars render in place:

```python
viewer.appendAnsiText("Downloading... 10%\rDownloading... 100%\n")
```

!!! tip "Ask for color"
    Many tools disable color when their output isn't a terminal. Pass their
    force-color flag (`--color=yes`, `--color=always`) or set
    `FORCE_COLOR=1` / `CLICOLOR_FORCE=1` in the process environment.

## Huge bursts without freezing

A log file or a chatty process can deliver 100k lines at once.
`appendAnsiTextAsync()` splits the text into line chunks inserted one per
event-loop turn, so the window stays responsive. The result is identical to
the synchronous path, including ANSI state, `\r` handling, timestamps, and
highlighting:

```python
viewer.appendAnsiTextAsync(huge_log, chunk_lines=500)
viewer.asyncAppendProgress.connect(
    lambda done, total: bar.setValue(100 * done // total)
)
viewer.asyncAppendFinished.connect(lambda: status.showMessage("done"))
```

`hasPendingAppends()` reports queued work and `cancelAsyncAppends()` drops
it (the chunk in flight still finishes).

## Output from worker threads

Call the viewer only from the GUI thread. From a worker, emit a signal
connected to the viewer; Qt queues the call across threads automatically:

```python
from PySide6.QtCore import QObject, Signal


class Worker(QObject):
    line = Signal(str)

    def run(self):
        for i in range(1000):
            self.line.emit(f"\x1b[36mstep {i}\x1b[0m\n")


worker.line.connect(viewer.appendAnsiText)
```

## Pause, resume, restart

- `pause_stream()` buffers incoming text instead of showing it, and
  `resume_stream()` flushes the buffer. The buffer is capped at 5000
  entries.
- `setClearOnStart(True)` plus a call to `beginNewStream()` whenever a new
  run starts wipes the previous run's output first.
- `clear()` resets text, ANSI state, search, bookmarks, and any queued async
  chunks, so cleared output can't come back from a pending chunk.

## Keep memory bounded

A pane that runs for hours needs limits. `setMaximumBlocks()` keeps the
newest lines and trims the oldest (default 10,000), and `setMaxLineLength()`
truncates hostile single lines (default 10,000 characters). Pass `0` to turn
either limit off:

```python
viewer.setMaximumBlocks(50_000)
viewer.setMaxLineLength(4_000)
```

Measured numbers are in [Limits and performance](../api/viewer.md#limits-and-performance).
For output you don't control, also read the note on
[untrusted logs](../index.md#api-reference).
