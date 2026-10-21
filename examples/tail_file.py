"""Follow a growing log file, like ``tail -f``.

Run with ``uv run python examples/tail_file.py path/to/app.log``. Without a
path, it writes a demo log to a temporary file and follows that. The file is
polled, which works on every platform and for files written by any program;
if the file shrinks (log rotation, truncation) it starts again from the top.
"""

import codecs
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ansi_text_viewer import AnsiTextViewer


class FileTail:
    """Poll *path* and append new bytes to *viewer*."""

    def __init__(self, viewer: AnsiTextViewer, path: Path, interval_ms: int = 250):
        """Start following *path* from its beginning."""
        self.viewer = viewer
        self.path = path
        self.offset = 0
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.timer = QTimer(interval=interval_ms)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        self.poll()

    def poll(self) -> None:
        """Read anything appended since the last poll."""
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            return
        if size < self.offset:  # rotated or truncated
            self.offset = 0
            self.decoder.reset()
            self.viewer.appendAnsiText(
                f"\x1b[33m--- {self.path.name} truncated ---\x1b[0m\n"
            )
        if size == self.offset:
            return
        with self.path.open("rb") as f:
            f.seek(self.offset)
            data = f.read()
        self.offset += len(data)
        self.viewer.appendAnsiText(self.decoder.decode(data))


DEMO_LINES = [
    "\x1b[32mINFO \x1b[0m worker started (pid 4120)",
    "\x1b[36mDEBUG\x1b[0m polling queue 'jobs'",
    "\x1b[32mINFO \x1b[0m job 17 done in 220ms",
    "\x1b[33mWARN \x1b[0m job 18 retry 1/3",
    "\x1b[31mERROR\x1b[0m job 18 failed: connection reset",
]


def demo_writer(path: Path) -> QTimer:
    """Append a demo line to *path* every 600 ms."""
    count = iter(range(10**9))

    def write():
        n = next(count)
        with path.open("a", encoding="utf-8") as f:
            f.write(DEMO_LINES[n % len(DEMO_LINES)] + "\n")

    timer = QTimer(interval=600)
    timer.timeout.connect(write)
    timer.start()
    return timer


def build(path: Path) -> tuple[AnsiTextViewer, FileTail]:
    """Create a viewer following *path*."""
    viewer = AnsiTextViewer()
    viewer.setWindowTitle(f"tail -f {path}")
    return viewer, FileTail(viewer, path)


def main() -> None:
    """Follow the path given on the command line, or a demo file."""
    app = QApplication(sys.argv)
    if len(sys.argv) > 1:
        path, writer = Path(sys.argv[1]), None
    else:
        path = Path(tempfile.gettempdir()) / "qansitextviewer-demo.log"
        path.write_text("", encoding="utf-8")
        writer = demo_writer(path)
    viewer, tail = build(path)
    viewer.resize(820, 420)
    viewer.show()
    exit_code = app.exec()
    del writer, tail
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
