"""Tests for non-blocking async appends."""

from PySide6.QtGui import QTextCursor


def _wait_drained(qtbot, viewer, timeout=10000):
    qtbot.waitUntil(lambda: not viewer.hasPendingAppends(), timeout=timeout)


def test_async_delivers_in_order(qtbot, viewer):
    lines = "".join(f"line {i:04d}\n" for i in range(1000))
    viewer.appendAnsiTextAsync(lines, chunk_lines=100)
    assert viewer.hasPendingAppends() is True
    _wait_drained(qtbot, viewer)
    text = viewer.toPlainText()
    assert "line 0000" in text
    assert "line 0999" in text
    assert text.index("line 0000") < text.index("line 0999")


def test_async_matches_sync(qtbot, viewer):
    from ansi_text_viewer import AnsiTextViewer

    tricky = (
        "\x1b[31mred\nstill red\x1b[0m\nplain\n"
        "prog 1\rprog 2\ndone https://example.com\n"
    )
    sync_viewer = AnsiTextViewer()
    qtbot.addWidget(sync_viewer)
    sync_viewer.show()
    sync_viewer.setAnsiText(tricky)

    viewer.appendAnsiTextAsync(tricky, chunk_lines=1)
    _wait_drained(qtbot, viewer)
    assert viewer.toPlainText() == sync_viewer.toPlainText()


def test_async_ansi_state_across_chunks(qtbot, viewer):
    viewer.appendAnsiTextAsync("\x1b[31mred\nstill red\x1b[0m\n", chunk_lines=1)
    _wait_drained(qtbot, viewer)
    block = viewer.document().findBlockByNumber(1)
    cur = QTextCursor(viewer.document())
    cur.setPosition(block.position())
    cur.setPosition(block.position() + 1, QTextCursor.MoveMode.KeepAnchor)
    assert cur.charFormat().foreground().color().red() == 170


def test_async_progress_and_finished(qtbot, viewer):
    progress = []
    viewer.asyncAppendProgress.connect(lambda d, t: progress.append((d, t)))
    with qtbot.waitSignal(viewer.asyncAppendFinished, timeout=10000):
        viewer.appendAnsiTextAsync("a\n" * 500, chunk_lines=100)
    assert progress
    assert progress[-1][0] == progress[-1][1] == 500
    assert all(
        b >= a for a, b in zip([0] + [d for d, _ in progress], [d for d, _ in progress])
    )


def test_async_cancel_drops_pending(qtbot, viewer):
    viewer.appendAnsiTextAsync("x\n" * 20000, chunk_lines=100)
    dropped = viewer.cancelAsyncAppends()
    assert dropped > 0
    assert viewer.hasPendingAppends() is False
    qtbot.wait(200)
    assert viewer.document().blockCount() <= 2


def test_async_clear_drops_queue(qtbot, viewer):
    viewer.appendAnsiTextAsync("y\n" * 5000, chunk_lines=100)
    viewer.clear()
    assert viewer.hasPendingAppends() is False
    qtbot.wait(200)
    assert viewer.toPlainText().strip() == ""


def test_async_rejects_non_string(viewer):
    try:
        viewer.appendAnsiTextAsync(None)
        assert False
    except TypeError:
        pass


def test_async_empty_is_noop(qtbot, viewer):
    viewer.appendAnsiTextAsync("")
    assert viewer.hasPendingAppends() is False
