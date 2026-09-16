"""Performance guards: generous bounds that only fail on algorithmic regress.

Bounds are ~30x current timings so slow CI runners do not flake; they
catch O(n^2) regressions such as per-append full-document scans.
"""

import time


def _rich_viewer(viewer):
    viewer.setLogLevelHighlighting(True)
    viewer.setSyntaxHighlighting(True)
    viewer.setLinksEnabled(True)
    return viewer


def test_bulk_append_stays_linear(viewer):
    _rich_viewer(viewer)
    start = time.time()
    viewer.setAnsiText("[INFO] hello world https://example.com\n" * 3000)
    assert time.time() - start < 10


def test_streaming_append_stays_linear(viewer):
    _rich_viewer(viewer)
    start = time.time()
    for i in range(1000):
        viewer.appendAnsiText(f"[INFO] stream line {i} https://example.com\n")
    assert time.time() - start < 8
