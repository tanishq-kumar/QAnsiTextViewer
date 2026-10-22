"""A small command runner: type a command, press Run, watch it stream.

Run with ``uv run python examples/run_command.py``. Output is decoded
incrementally, the view clears on every new run, and the exit code is
reported in color when the process ends.
"""

import codecs
import shlex
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ansi_text_viewer import AnsiTextViewer

# A self-contained default so the example works anywhere Python runs.
DEMO = r"""
import time
for step in range(0, 101, 25):
    print(f"\rbuilding... {step}%", end="", flush=True)
    time.sleep(0.15)
print()
print("\x1b[32mok\x1b[0m   compiled 12 modules")
print("\x1b[33mwarn\x1b[0m unused import in utils.py:3")
print("\x1b[31mfail\x1b[0m test_session.py::test_load")
raise SystemExit(1)
"""


class CommandRunner(QWidget):
    """A command line, Run/Stop buttons, and a viewer for the output."""

    def __init__(self):
        """Build the window and wire the process signals."""
        super().__init__()
        self.setWindowTitle("Run a command")
        self.command = QLineEdit(placeholderText="Command to run (empty: demo build)")
        self.run_button = QPushButton("Run")
        self.stop_button = QPushButton("Stop", enabled=False)
        self.viewer = AnsiTextViewer()
        self.viewer.setClearOnStart(True)

        bar = QHBoxLayout()
        bar.addWidget(self.command)
        bar.addWidget(self.run_button)
        bar.addWidget(self.stop_button)
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.viewer)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.run_button.clicked.connect(self.run)
        self.stop_button.clicked.connect(self.process.kill)

    def run(self) -> None:
        """Start the typed command, or the demo build when the box is empty."""
        text = self.command.text().strip()
        args = shlex.split(text) if text else [sys.executable, "-c", DEMO]
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.viewer.beginNewStream()
        self.viewer.appendAnsiText(f"\x1b[90m$ {text or 'demo build'}\x1b[0m\n")
        self.process.start(args[0], args[1:])
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def read_output(self) -> None:
        """Append whatever the process has written so far."""
        data = self.process.readAllStandardOutput().data()
        self.viewer.appendAnsiText(self.decoder.decode(data))

    def finished(self, code: int, status: QProcess.ExitStatus) -> None:
        """Report the exit code and re-enable Run."""
        self.viewer.appendAnsiText(self.decoder.decode(b"", final=True))
        color = "32" if code == 0 else "31"
        self.viewer.appendAnsiText(f"\x1b[{color}m[exit {code}]\x1b[0m\n")
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)


def build() -> CommandRunner:
    """Create the runner window."""
    return CommandRunner()


def main() -> None:
    """Show the runner."""
    app = QApplication(sys.argv)
    runner = build()
    runner.resize(820, 420)
    runner.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
