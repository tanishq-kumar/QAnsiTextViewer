from PySide6.QtWidgets import QApplication
from ansi_text_viewer import AnsiTextViewer

app = QApplication([])
viewer = AnsiTextViewer()
viewer.setTheme("dark")
viewer.appendAnsiText("\x1b[31mred\x1b[0m plain\n")
viewer.highlight_search("red")  # F3 / Shift+F3 navigates, Esc clears
viewer.show()
app.exec()