"""Shared light/dark switching for the screenshot scripts."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ansi_text_viewer import AnsiTextViewer


def dark_palette() -> QPalette:
    """Return a dark Fusion palette that matches the viewer's dark theme."""
    p = QPalette()
    window, base, text = QColor(45, 45, 45), QColor(30, 30, 30), QColor(220, 220, 220)
    for role, color in (
        (QPalette.ColorRole.Window, window),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, base),
        (QPalette.ColorRole.AlternateBase, window),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, QColor(53, 53, 53)),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.ToolTipBase, base),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.PlaceholderText, QColor(140, 140, 140)),
        (QPalette.ColorRole.Highlight, QColor(42, 130, 218)),
        (QPalette.ColorRole.HighlightedText, QColor(255, 255, 255)),
        (QPalette.ColorRole.Link, QColor(90, 160, 255)),
    ):
        p.setColor(role, color)
    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.WindowText,
    ):
        p.setColor(disabled, role, QColor(110, 110, 110))
    return p


_original_init = AnsiTextViewer.__init__


def use_theme(app: QApplication, theme: str) -> None:
    """Switch the application palette, and start every new viewer in *theme*.

    The viewer colors text when it is appended, so a viewer switched to dark
    after its content arrived keeps light backgrounds behind that text. New
    viewers therefore get the pass theme before any code appends to them.
    """
    app.setStyle("Fusion")
    app.setPalette(dark_palette() if theme == "dark" else app.style().standardPalette())

    def init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        self.setTheme(theme)

    AnsiTextViewer.__init__ = init


def suffixed(name: str, theme: str) -> str:
    """Return ``name.png`` for light and ``name_dark.png`` for dark."""
    return name if theme == "light" else name.replace(".png", "_dark.png")
