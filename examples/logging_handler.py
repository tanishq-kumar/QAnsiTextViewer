"""Route Python ``logging`` into an AnsiTextViewer, colored by level.

Run with ``uv run python examples/logging_handler.py``. Records logged from
any thread land in the viewer, because the handler hands each line to the
GUI thread through a queued Qt signal.
"""

import logging
import random
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ansi_text_viewer import AnsiTextViewer

LEVEL_COLORS = {
    logging.DEBUG: "36",  # cyan
    logging.INFO: "32",  # green
    logging.WARNING: "33",  # yellow
    logging.ERROR: "31",  # red
    logging.CRITICAL: "1;31",  # bold red
}


class AnsiFormatter(logging.Formatter):
    """Format records normally, then color the level name."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the formatted record with its level name in ANSI color."""
        text = super().format(record)
        color = LEVEL_COLORS.get(record.levelno, "0")
        colored = f"\x1b[{color}m{record.levelname}\x1b[0m"
        return text.replace(record.levelname, colored, 1)


class _Bridge(QObject):
    line = Signal(str)


class ViewerHandler(logging.Handler):
    """A logging handler that appends to a viewer, safe from any thread."""

    def __init__(self, viewer: AnsiTextViewer):
        """Connect to *viewer*; the connection is queued across threads."""
        super().__init__()
        self._bridge = _Bridge()
        self._bridge.line.connect(viewer.appendAnsiText)

    def emit(self, record: logging.LogRecord) -> None:
        """Send one formatted record to the viewer."""
        try:
            self._bridge.line.emit(self.format(record) + "\n")
        except Exception:
            self.handleError(record)


def build() -> tuple[AnsiTextViewer, logging.Logger]:
    """Create the viewer and a logger that writes into it."""
    viewer = AnsiTextViewer()
    viewer.setWindowTitle("logging -> AnsiTextViewer")
    handler = ViewerHandler(viewer)
    handler.setFormatter(
        AnsiFormatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%H:%M:%S")
    )
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return viewer, logger


SAMPLES = [
    (logging.INFO, "server listening on :8080"),
    (logging.DEBUG, "cache warmed with 412 entries"),
    (logging.WARNING, "slow query took 1.8s"),
    (logging.ERROR, "upstream returned 502"),
    (logging.INFO, "request served in 41ms"),
    (logging.CRITICAL, "disk almost full (98%)"),
]


def worker(logger: logging.Logger, stop: threading.Event) -> None:
    """Log from a background thread to show the handler is thread-safe."""
    log = logger.getChild("worker")
    while not stop.wait(1.3):
        log.info("background job tick")


def main() -> None:
    """Show the viewer and keep logging sample records."""
    app = QApplication(sys.argv)
    viewer, logger = build()
    viewer.resize(820, 420)
    viewer.show()

    timer = QTimer(interval=700)
    timer.timeout.connect(lambda: logger.log(*random.choice(SAMPLES)))
    timer.start()

    stop = threading.Event()
    threading.Thread(target=worker, args=(logger, stop), daemon=True).start()
    app.aboutToQuit.connect(stop.set)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
