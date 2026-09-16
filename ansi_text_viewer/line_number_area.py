"""Gutter widget showing line numbers and bookmark markers."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QWidget


class LineNumberArea(QWidget):
    """Narrow widget beside the viewer for numbers and bookmark clicks."""

    def __init__(self, viewer):
        """Create the gutter for *viewer*."""
        super().__init__(viewer)
        self.viewer = viewer
        self.setToolTip("Click to bookmark / unbookmark line")

    def sizeHint(self):
        """Return the gutter width requested by the viewer."""
        return QSize(self.viewer.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent):
        """Delegate painting to the viewer."""
        self.viewer.lineNumberAreaPaintEvent(event)

    def mousePressEvent(self, event):
        """Toggle the bookmark of the clicked line."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.viewer.toggleBookmarkAtY(int(event.position().y())) >= 0:
                event.accept()
                return
        super().mousePressEvent(event)
