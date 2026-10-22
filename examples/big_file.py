"""Open a huge log without freezing the window.

Run with ``uv run python examples/big_file.py path/to/huge.log``. Without a
path, it generates 200,000 colored lines. The text goes in through
``appendAnsiTextAsync()``, one chunk per event-loop turn, while a progress
bar follows along and Cancel stops the rest.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ansi_text_viewer import AnsiTextViewer

LEVELS = ["\x1b[32mINFO \x1b[0m", "\x1b[36mDEBUG\x1b[0m", "\x1b[33mWARN \x1b[0m"]


def synthetic_log(lines: int) -> str:
    """Return *lines* lines of colored sample log text."""
    return "".join(
        f"{LEVELS[i % 3]} request {i:>6} handled in {i % 97 + 3}ms\n"
        for i in range(lines)
    )


class BigFileWindow(QWidget):
    """A viewer, a progress bar, and a Cancel button."""

    def __init__(self):
        """Build the window and wire the async progress signals."""
        super().__init__()
        self.setWindowTitle("Big file")
        self.viewer = AnsiTextViewer()
        self.viewer.setMaximumBlocks(250_000)  # default keeps the newest 10,000
        self.progress = QProgressBar()
        self.status = QLabel("idle")
        self.cancel = QPushButton("Cancel", enabled=False)
        self.total = 0

        bar = QHBoxLayout()
        bar.addWidget(self.progress, 1)
        bar.addWidget(self.status)
        bar.addWidget(self.cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(self.viewer)
        layout.addLayout(bar)

        self.viewer.asyncAppendProgress.connect(self.on_progress)
        self.viewer.asyncAppendFinished.connect(self.on_finished)
        self.cancel.clicked.connect(self.on_cancel)

    def load(self, text: str) -> None:
        """Queue *text* for non-blocking insertion."""
        self.viewer.clear()
        self.total = 0
        self.cancel.setEnabled(True)
        self.status.setText("loading...")
        self.viewer.appendAnsiTextAsync(text, chunk_lines=2000)

    def on_progress(self, done: int, total: int) -> None:
        """Mirror the async queue in the progress bar."""
        self.total = total
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status.setText(f"{done:,} / {total:,} lines")

    def on_finished(self) -> None:
        """Report completion."""
        self.cancel.setEnabled(False)
        self.status.setText(f"done, {self.total:,} lines")

    def on_cancel(self) -> None:
        """Drop whatever has not been inserted yet."""
        dropped = self.viewer.cancelAsyncAppends()
        self.cancel.setEnabled(False)
        self.status.setText(f"cancelled ({dropped} chunks dropped)")


def build() -> BigFileWindow:
    """Create the window."""
    return BigFileWindow()


def main() -> None:
    """Load the file named on the command line, or generated lines."""
    app = QApplication(sys.argv)
    window = build()
    window.resize(820, 480)
    window.show()
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    else:
        text = synthetic_log(200_000)
    window.load(text)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
