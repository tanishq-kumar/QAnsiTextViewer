import os

# Must be set before any Qt imports for headless CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from ansi_text_viewer import AnsiTextViewer
from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler


@pytest.fixture
def handler():
    return AnsiEscapeHandler()


@pytest.fixture
def viewer(qtbot):
    w = AnsiTextViewer()
    qtbot.addWidget(w)
    w.show()
    return w
