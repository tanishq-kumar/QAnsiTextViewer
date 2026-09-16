import time


def test_ansi_huge_repeat_clamped(viewer):
    start = time.time()
    viewer.appendAnsiText("\x1b[999999999Cafter\n")
    assert time.time() - start < 5
    assert "after" in viewer.toPlainText()


def test_ansi_huge_digit_run_clamped():
    from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler

    h = AnsiEscapeHandler()
    actions = h.parse("\x1b[" + "9" * 100000 + "C")
    assert actions[0][1] <= 10000


def test_invalid_regex_safe(viewer):
    assert viewer.highlight_search("([", use_regex=True) == 0
    viewer.filter_search("([", use_regex=True)  # must not raise


def test_long_regex_bounded(viewer):
    assert viewer.highlight_search("a" * 600, use_regex=True) == 0


def test_session_validation(viewer, tmp_path):
    import json

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"text": "x" * (6 * 1024 * 1024)}), encoding="utf-8")
    try:
        viewer.loadSession(str(bad))
        assert False, "should have raised"
    except ValueError:
        pass

    bad2 = tmp_path / "bad2.json"
    bad2.write_text("not json", encoding="utf-8")
    try:
        viewer.loadSession(str(bad2))
        assert False, "should have raised"
    except Exception:
        pass


def test_maxblocks_bounded(viewer):
    viewer.setMaximumBlocks(10**9)
    assert viewer.maximumBlocks() <= 200000
    viewer.setMaximumBlocks(10000)
