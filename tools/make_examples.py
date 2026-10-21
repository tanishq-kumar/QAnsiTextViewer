"""Run every script in ``examples/`` and grab its window for the docs.

Run with ``QT_QPA_FONTDIR=C:/Windows/Fonts uv run python tools/make_examples.py``.
Each example is imported and driven the way a user would drive it (logging
records, a real subprocess, a growing file, a big async load); the script
checks the outcome before saving the picture, so it doubles as a smoke test.
"""

import importlib
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "examples"))

from darkmode import suffixed, use_theme  # noqa: E402
from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

OUT = ROOT / "docs" / "assets"
THEME = "light"  # set per pass in __main__


def wait(condition, timeout: float = 10.0) -> None:
    """Pump the event loop until *condition()* is true or *timeout* passes."""
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("example did not reach the expected state")
        QCoreApplication.processEvents()
        time.sleep(0.01)


def shoot(widget: QWidget, name: str, size: tuple[int, int]) -> None:
    """Show *widget* at *size*, grab it to ``docs/assets/<name>``, close it."""
    widget.resize(*size)
    widget.show()
    for _ in range(3):
        QCoreApplication.processEvents()
    widget.grab().save(str(OUT / suffixed(name, THEME)))
    widget.close()
    print("wrote", suffixed(name, THEME))


def mono(viewer) -> None:
    """Use a fixed font that exists on the build machine."""
    viewer.setMonospaceFont("Consolas", 11)


class FixedClock(logging.Filter):
    """Give records fixed timestamps so reruns match."""

    t = 1760000000.0

    def filter(self, record):
        """Assign the next timestamp."""
        record.created = FixedClock.t
        FixedClock.t += 2.3
        return True


def logging_handler() -> None:
    """Log the sample records plus one from a worker thread."""
    ex = importlib.import_module("logging_handler")
    viewer, logger = ex.build()
    mono(viewer)
    logger.handlers[-1].addFilter(FixedClock())
    for level, message in ex.SAMPLES:
        logger.log(level, message)
    t = threading.Thread(
        target=lambda: logger.getChild("worker").info("background job tick")
    )
    t.start()
    t.join()
    wait(lambda: "background job tick" in viewer.toPlainText())
    shoot(viewer, "example_logging_handler.png", (760, 200))


def run_command() -> None:
    """Run the default demo command to completion."""
    ex = importlib.import_module("run_command")
    runner = ex.build()
    mono(runner.viewer)
    runner.run()
    wait(lambda: "[exit 1]" in runner.viewer.toPlainText())
    shoot(runner, "example_run_command.png", (760, 260))


def tail_file() -> None:
    """Follow a temp file while lines are appended, then truncate it."""
    ex = importlib.import_module("tail_file")
    path = Path(tempfile.mkdtemp()) / "app.log"
    path.write_text("", encoding="utf-8")
    viewer, tail = ex.build(path)
    mono(viewer)
    viewer.setWindowTitle("tail -f app.log")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(ex.DEMO_LINES[:4]) + "\n")
    tail.poll()
    path.write_text(ex.DEMO_LINES[4] + "\n", encoding="utf-8")
    tail.poll()
    assert "truncated" in viewer.toPlainText()
    tail.timer.stop()
    shoot(viewer, "example_tail_file.png", (760, 170))


def custom_highlight() -> None:
    """Show the sample access log with the three custom rules."""
    ex = importlib.import_module("custom_highlight")
    viewer = ex.build()
    mono(viewer)
    shoot(viewer, "example_custom_highlight.png", (760, 190))


def big_file() -> None:
    """Load 60,000 generated lines asynchronously to completion."""
    ex = importlib.import_module("big_file")
    window = ex.build()
    mono(window.viewer)
    window.load(ex.synthetic_log(60_000))
    wait(lambda: window.status.text().startswith("done"), timeout=60)
    shoot(window, "example_big_file.png", (760, 260))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    for THEME in ("light", "dark"):
        use_theme(app, THEME)
        FixedClock.t = 1760000000.0
        logging.getLogger("app").handlers.clear()
        logging_handler()
        run_command()
        tail_file()
        custom_highlight()
        big_file()
