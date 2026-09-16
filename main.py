import sys

from PySide6.QtWidgets import QApplication

from demo import TestWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    win = TestWindow()
    win.setWindowTitle("QAnsiTextViewer")
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
