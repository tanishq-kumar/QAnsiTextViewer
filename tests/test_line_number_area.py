from PySide6.QtCore import QSize


def test_size_hint_matches_viewer_width(viewer):
    hint = viewer.lineNumberArea.sizeHint()
    assert isinstance(hint, QSize)
    assert hint.width() == viewer.lineNumberAreaWidth()


def test_viewer_reference(viewer):
    assert viewer.lineNumberArea.viewer is viewer
