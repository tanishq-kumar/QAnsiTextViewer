"""Tests for font selection: size, family, and system font adoption."""


def test_font_size_clamps_and_sticks(viewer):
    viewer.setFontSize(14)
    assert viewer.font().pointSize() == 14
    viewer.zoomIn(2)
    assert viewer.font().pointSize() > 14
    viewer.resetZoom()
    assert viewer.font().pointSize() == 14
    viewer.setFontSize(1000)
    assert viewer.font().pointSize() == 72
    viewer.setFontSize(1)
    assert viewer.font().pointSize() == 6
    before = viewer.font().pointSize()
    viewer.setFontSize("huge")
    assert viewer.font().pointSize() == before


def test_font_family_changes(viewer):
    viewer.setFontFamily("Courier New")
    assert viewer.font().family() == "Courier New"
    viewer.setFontFamily("")
    assert viewer.font().family() == "Courier New"


def test_use_system_font(qtbot):
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from ansi_text_viewer import AnsiTextViewer

    app = QApplication.instance()
    app.setFont(QFont("Arial", 13))
    try:
        viewer = AnsiTextViewer()
        qtbot.addWidget(viewer)
        viewer.show()
        viewer.useSystemFont()
        assert viewer.font().family() == "Arial"
        assert viewer.font().pointSize() == 13
    finally:
        app.setFont(QFont())
