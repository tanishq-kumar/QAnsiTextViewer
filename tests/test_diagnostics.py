"""Tests that silent fallbacks explain themselves via debug logs."""

import logging


def test_invalid_regex_logs(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer.search_handler"):
        assert viewer.highlight_search("([", use_regex=True) == 0
    assert any("invalid regex" in r.message for r in caplog.records)


def test_long_regex_logs_and_rejects(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        assert viewer.highlight_search("a" * 600, use_regex=True) == 0
    assert any("rejected" in r.message for r in caplog.records)
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        viewer.filter_search("b" * 600, use_regex=True)
    assert any("rejected" in r.message for r in caplog.records)


def test_clamped_settings_log(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        viewer.setMaximumBlocks(10**9)
        viewer.setMaxLineLength(10**9)
        viewer.setFontSize(1000)
    assert sum("clamped" in r.message for r in caplog.records) == 3
    viewer.setMaximumBlocks(10000)


def test_pause_trim_logs(viewer, caplog):
    viewer.pause_stream()
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        for i in range(5010):
            viewer.appendAnsiText(f"line {i}\n")
    assert any("pause buffer full" in r.message for r in caplog.records)
    viewer.resume_stream()


def test_cancel_logs_dropped_count(viewer, caplog):
    viewer.appendAnsiTextAsync("x\n" * 2000, chunk_lines=100)
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        dropped = viewer.cancelAsyncAppends()
    assert dropped > 0
    assert any(str(dropped) in r.message for r in caplog.records)


def test_cancel_empty_is_silent(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        assert viewer.cancelAsyncAppends() == 0
    assert not [r for r in caplog.records if "cancelAsyncAppends" in r.message]


def test_bad_gutter_click_logs(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        assert viewer.toggleBookmarkAtY(-1000) == -1
    assert any("no visible block" in r.message for r in caplog.records)


def test_bad_bookmark_logs(viewer, caplog):
    with caplog.at_level(logging.DEBUG, logger="ansi_text_viewer"):
        assert viewer.toggleBookmark(999999) is False
    assert any("no block" in r.message for r in caplog.records)
