# Examples

Five small programs, each one job you are likely to need. They live in the
repository's `examples/` folder and run as they are:

```bash
uv run python examples/logging_handler.py
```

Every screenshot on this page comes from running the example itself (see
`tools/make_examples.py`), and the code shown is the file, included
verbatim.

## Python logging, colored by level

Route the standard `logging` module into the viewer. The handler colors the
level name and hands each line to the GUI thread through a queued signal, so
records logged from worker threads are safe too.

<figure class="gb-figure gb-hero" markdown>
![Seven log records in the viewer with colored INFO, DEBUG, WARNING, ERROR and bold CRITICAL level names, the last one logged from a worker thread](assets/example_logging_handler.png#only-light){ width="760" }
![Seven log records in the viewer with colored INFO, DEBUG, WARNING, ERROR and bold CRITICAL level names, the last one logged from a worker thread](assets/example_logging_handler_dark.png#only-dark){ width="760" }
<figcaption>Sample records, the last one from a background thread.</figcaption>
</figure>

??? example "examples/logging_handler.py"

    ```python title="examples/logging_handler.py" linenums="1"
    --8<-- "examples/logging_handler.py"
    ```

## Run a command

A command box with Run and Stop. Output streams in as the process writes it,
`\r` progress lines overwrite in place, the view clears on each run, and the
exit code is reported in green or red. Leave the box empty to run a built-in
demo build.

<figure class="gb-figure gb-hero" markdown>
![The command runner after the demo build: a progress line at 100%, ok, warn and fail lines in color, a clickable utils.py:3 link, and a red exit 1](assets/example_run_command.png#only-light){ width="760" }
![The command runner after the demo build: a progress line at 100%, ok, warn and fail lines in color, a clickable utils.py:3 link, and a red exit 1](assets/example_run_command_dark.png#only-dark){ width="760" }
<figcaption>The demo build run to completion; <code>utils.py:3</code> is a clickable file link.</figcaption>
</figure>

??? example "examples/run_command.py"

    ```python title="examples/run_command.py" linenums="1"
    --8<-- "examples/run_command.py"
    ```

## Follow a log file

`tail -f` for any file: pass a path, or run it without one to follow a demo
log. The file is polled, which works on every platform and for files any
program writes; when the file shrinks (rotation, truncation) the view says so
and starts again from the top.

<figure class="gb-figure gb-hero" markdown>
![Six colored lines followed from app.log, with a yellow notice where the file was truncated](assets/example_tail_file.png#only-light){ width="760" }
![Six colored lines followed from app.log, with a yellow notice where the file was truncated](assets/example_tail_file_dark.png#only-dark){ width="760" }
<figcaption>Four lines appended, then the file truncated and written again.</figcaption>
</figure>

??? example "examples/tail_file.py"

    ```python title="examples/tail_file.py" linenums="1"
    --8<-- "examples/tail_file.py"
    ```

## Your own highlight rules

Plain text with no ANSI codes can still be colored. Three small rules dim
client addresses, color HTTP status codes by class, and bold every timing.
See [Highlighting](api/highlighting.md) for the rule protocol.

<figure class="gb-figure gb-hero" markdown>
![An access log with gray IP addresses, status codes colored green, blue, amber and red by class, and orange bold durations](assets/example_custom_highlight.png#only-light){ width="760" }
![An access log with gray IP addresses, status codes colored green, blue, amber and red by class, and orange bold durations](assets/example_custom_highlight_dark.png#only-dark){ width="760" }
<figcaption>An access log colored by three custom rules.</figcaption>
</figure>

??? example "examples/custom_highlight.py"

    ```python title="examples/custom_highlight.py" linenums="1"
    --8<-- "examples/custom_highlight.py"
    ```

## Open a huge log

Load hundreds of thousands of lines without freezing the window:
`appendAnsiTextAsync()` inserts one chunk per event-loop turn, a progress bar
follows `asyncAppendProgress`, and Cancel drops the rest. The example raises
`setMaximumBlocks()`, since the default keeps only the newest 10,000 lines.

<figure class="gb-figure gb-hero" markdown>
![The big-file window after loading 60,000 generated lines: the end of the log, a full progress bar, and the status done, 60,000 lines](assets/example_big_file.png#only-light){ width="760" }
![The big-file window after loading 60,000 generated lines: the end of the log, a full progress bar, and the status done, 60,000 lines](assets/example_big_file_dark.png#only-dark){ width="760" }
<figcaption>60,000 generated lines, loaded in the background.</figcaption>
</figure>

??? example "examples/big_file.py"

    ```python title="examples/big_file.py" linenums="1"
    --8<-- "examples/big_file.py"
    ```
