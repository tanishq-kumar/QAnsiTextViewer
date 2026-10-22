"""Smoke tests: every script in examples/ builds and does its job."""

import importlib
import logging
import sys
import threading
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture(autouse=True)
def examples_on_path(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLES))


def load(name):
    return importlib.import_module(name)


def test_logging_handler_colors_levels_from_any_thread(qtbot):
    ex = load("logging_handler")
    viewer, logger = ex.build()
    qtbot.addWidget(viewer)
    logger.propagate = False
    logger.error("upstream returned 502")
    t = threading.Thread(target=lambda: logger.warning("from a worker"))
    t.start()
    t.join()
    qtbot.waitUntil(lambda: "from a worker" in viewer.toPlainText())
    assert "ERROR" in viewer.toPlainText()
    logger.handlers.clear()


def test_run_command_streams_demo_and_reports_exit(qtbot):
    ex = load("run_command")
    runner = ex.build()
    qtbot.addWidget(runner)
    runner.run()
    qtbot.waitUntil(lambda: "[exit 1]" in runner.viewer.toPlainText(), timeout=15000)
    text = runner.viewer.toPlainText()
    assert "building... 100%" in text
    assert "building... 0%" not in text  # \r overwrote the progress line


def test_tail_file_follows_appends_and_truncation(qtbot, tmp_path):
    ex = load("tail_file")
    path = tmp_path / "app.log"
    path.write_text("first\n", encoding="utf-8")
    viewer, tail = ex.build(path)
    qtbot.addWidget(viewer)
    tail.timer.stop()
    with path.open("a", encoding="utf-8") as f:
        f.write("second\n")
    tail.poll()
    assert "first" in viewer.toPlainText() and "second" in viewer.toPlainText()
    path.write_text("x\n", encoding="utf-8")
    tail.poll()
    assert "truncated" in viewer.toPlainText()


def test_custom_highlight_rules_find_spans():
    ex = load("custom_highlight")
    line = '10.0.0.44 - - "POST /api/v1/upload HTTP/1.1" 502 0 30.0s'
    (status,) = ex.StatusRule().spans(line)
    assert line[status.start : status.end] == "502"
    (duration,) = ex.DurationRule().spans(line)
    assert line[duration.start : duration.end] == "30.0s"
    (ip,) = ex.IpRule().spans(line)
    assert line[ip.start : ip.end] == "10.0.0.44"


def test_big_file_loads_async_to_completion(qtbot):
    ex = load("big_file")
    window = ex.build()
    qtbot.addWidget(window)
    window.load(ex.synthetic_log(5000))
    qtbot.waitUntil(lambda: window.status.text().startswith("done"), timeout=15000)
    assert window.status.text() == "done, 5,000 lines"


@pytest.fixture(autouse=True)
def _quiet_logging():
    yield
    logging.getLogger("app").handlers.clear()
    for name in list(sys.modules):
        if name in {
            "logging_handler",
            "run_command",
            "tail_file",
            "custom_highlight",
            "big_file",
        }:
            del sys.modules[name]
