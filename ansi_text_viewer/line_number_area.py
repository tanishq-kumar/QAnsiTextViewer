from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPaintEvent
from PySide6.QtCore import QSize

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent):
        self.codeEditor.lineNumberAreaPaintEvent(event)
