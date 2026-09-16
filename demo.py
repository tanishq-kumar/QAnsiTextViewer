"""Full demo application for QAnsiTextViewer.

Run with ``uv run python demo.py`` (or ``just demo``).
"""

import logging
import random
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ansi_text_viewer import AnsiTextViewer

ESC = "\x1b"

ANSI_SEQUENCES = [
    # --- text styles ---
    (ESC + "[0m", "reset all"),
    (ESC + "[1m", "bold"),
    (ESC + "[2m", "dim"),
    (ESC + "[3m", "italic"),
    (ESC + "[4m", "underline"),
    (ESC + "[5m", "blink slow"),
    (ESC + "[7m", "reverse/invert"),
    (ESC + "[9m", "strikethrough"),
    # --- foreground colors ---
    (ESC + "[30m", "fg black"),
    (ESC + "[31m", "fg red"),
    (ESC + "[32m", "fg green"),
    (ESC + "[33m", "fg yellow"),
    (ESC + "[34m", "fg blue"),
    (ESC + "[35m", "fg magenta"),
    (ESC + "[36m", "fg cyan"),
    (ESC + "[37m", "fg white"),
    # --- bright foreground ---
    (ESC + "[90m", "fg bright black (gray)"),
    (ESC + "[91m", "fg bright red"),
    (ESC + "[92m", "fg bright green"),
    (ESC + "[93m", "fg bright yellow"),
    (ESC + "[94m", "fg bright blue"),
    (ESC + "[95m", "fg bright magenta"),
    (ESC + "[96m", "fg bright cyan"),
    (ESC + "[97m", "fg bright white"),
    # --- background colors ---
    (ESC + "[40m", "bg black"),
    (ESC + "[41m", "bg red"),
    (ESC + "[42m", "bg green"),
    (ESC + "[43m", "bg yellow"),
    (ESC + "[44m", "bg blue"),
    (ESC + "[45m", "bg magenta"),
    (ESC + "[46m", "bg cyan"),
    (ESC + "[47m", "bg white"),
    # --- 256-color mode ---
    (ESC + "[38;5;196m", "fg 256 red (196)"),
    (ESC + "[38;5;46m", "fg 256 green (46)"),
    (ESC + "[38;5;21m", "fg 256 blue (21)"),
    (ESC + "[48;5;196m", "bg 256 red (196)"),
    # --- true color (RGB) ---
    (ESC + "[38;2;255;165;0m", "fg RGB orange"),
    (ESC + "[38;2;128;0;128m", "fg RGB purple"),
    (ESC + "[48;2;255;127;80m", "bg RGB coral"),
]


class AnsiColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[36m",  # Cyan
        logging.INFO: "\x1b[32m",  # Green
        logging.WARNING: "\x1b[33m",  # Yellow
        logging.ERROR: "\x1b[31m",  # Red
        logging.CRITICAL: "\x1b[1;31m",  # Bold Red
    }
    RESET = "\x1b[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class AnsiLogHandler(logging.Handler):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

    def emit(self, record):
        log_entry = self.format(record)
        self.viewer.appendAnsiText(log_entry + "\n")


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 700)
        central = QWidget()
        layout = QVBoxLayout(central)
        self.total_matches = 0

        self.viewer = AnsiTextViewer()
        layout.addWidget(self.viewer)
        self.viewer.findRequested.connect(
            lambda: (self.search_input.setFocus(), self.search_input.selectAll())
        )
        self.viewer.nextRequested.connect(
            lambda: self.update_match_label(self.viewer.next_match())
        )
        self.viewer.prevRequested.connect(
            lambda: self.update_match_label(self.viewer.prev_match())
        )

        # Search Controls UI
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Highlight Search... (Ctrl+F)")
        self.search_input.textChanged.connect(self.do_search)

        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.clicked.connect(
            lambda: self.update_match_label(self.viewer.prev_match())
        )

        self.btn_next = QPushButton(">")
        self.btn_next.setFixedWidth(30)
        self.btn_next.clicked.connect(
            lambda: self.update_match_label(self.viewer.next_match())
        )

        self.match_label = QLabel("0/0")

        self.regex_cb = QCheckBox("Regex")
        self.regex_cb.stateChanged.connect(self.do_search)
        self.regex_cb.stateChanged.connect(self.do_filter)

        self.case_cb = QCheckBox("Match Case")
        self.case_cb.stateChanged.connect(self.do_search)
        self.case_cb.stateChanged.connect(self.do_filter)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_prev)
        search_layout.addWidget(self.btn_next)
        search_layout.addWidget(self.match_label)
        search_layout.addWidget(self.regex_cb)
        search_layout.addWidget(self.case_cb)
        layout.addLayout(search_layout)

        # Filter Control UI
        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter lines containing text...")
        self.filter_input.textChanged.connect(self.do_filter)
        filter_layout.addWidget(QLabel("Hide Blocks Filter:"))
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)

        # Other Options UI
        viewer_controls = QHBoxLayout()
        self.autoscroll_cb = QCheckBox("Auto Scroll")
        self.autoscroll_cb.setChecked(True)
        self.autoscroll_cb.stateChanged.connect(
            lambda state: self.viewer.setAutoScroll(bool(state))
        )
        viewer_controls.addWidget(self.autoscroll_cb)

        self.line_numbers_cb = QCheckBox("Line Numbers")
        self.line_numbers_cb.setChecked(True)
        self.line_numbers_cb.stateChanged.connect(
            lambda state: self.viewer.setLineNumbersVisible(bool(state))
        )
        viewer_controls.addWidget(self.line_numbers_cb)

        self.wrap_cb = QCheckBox("Word Wrap")
        self.wrap_cb.setChecked(False)
        self.wrap_cb.stateChanged.connect(
            lambda state: self.viewer.setWordWrapEnabled(bool(state))
        )
        viewer_controls.addWidget(self.wrap_cb)

        self.timestamp_cb = QCheckBox("Timestamp")
        self.timestamp_cb.stateChanged.connect(
            lambda state: self.viewer.setTimestampEnabled(bool(state))
        )
        viewer_controls.addWidget(self.timestamp_cb)

        self.loglevel_cb = QCheckBox("Log Levels")
        self.loglevel_cb.setChecked(True)
        self.loglevel_cb.stateChanged.connect(
            lambda state: self.viewer.setLogLevelHighlighting(bool(state))
        )
        viewer_controls.addWidget(self.loglevel_cb)
        self.viewer.setLogLevelHighlighting(True)
        self.viewer.setSyntaxHighlighting(True)

        self.curline_cb = QCheckBox("Current Line")
        self.curline_cb.stateChanged.connect(
            lambda state: self.viewer.setCurrentLineHighlightEnabled(bool(state))
        )
        viewer_controls.addWidget(self.curline_cb)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.currentTextChanged.connect(
            lambda mode: self.viewer.setTheme(mode.lower())
        )
        viewer_controls.addWidget(QLabel("Theme:"))
        viewer_controls.addWidget(self.theme_combo)

        self.match_theme_cb = QCheckBox("Match theme colors")
        self.match_theme_cb.setChecked(True)
        self.match_theme_cb.setToolTip(
            "Default text colors follow the theme; uncheck to pick your own"
        )
        self.match_theme_cb.stateChanged.connect(
            lambda state: self.viewer.setColorsFollowTheme(bool(state))
        )
        viewer_controls.addWidget(self.match_theme_cb)

        self.fg_pick = QPushButton("Text color...")
        self.fg_pick.clicked.connect(lambda: self.pick_default_color("fg"))
        viewer_controls.addWidget(self.fg_pick)

        self.bg_pick = QPushButton("Background...")
        self.bg_pick.clicked.connect(lambda: self.pick_default_color("bg"))
        viewer_controls.addWidget(self.bg_pick)

        self.clear_start_cb = QCheckBox("Clear on Start")
        self.clear_start_cb.stateChanged.connect(
            lambda state: self.viewer.setClearOnStart(bool(state))
        )
        viewer_controls.addWidget(self.clear_start_cb)

        viewer_controls.addStretch()
        layout.addLayout(viewer_controls)

        # Palette picker
        pal_layout = QHBoxLayout()
        pal_layout.addWidget(QLabel("Palette:"))

        self.pal_combo = QComboBox()
        names = [
            "black",
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "white",
        ]
        self.pal_combo.addItems([f"{n} ({name})" for n, name in enumerate(names)])
        self.pal_combo.setCurrentIndex(1)
        pal_layout.addWidget(self.pal_combo)
        self.pal_pick = QPushButton("Pick Color...")
        self.pal_pick.clicked.connect(self.pick_palette_color)
        pal_layout.addWidget(self.pal_pick)
        self.pal_reset = QPushButton("Reset Palette")
        self.pal_reset.clicked.connect(self.viewer.resetAnsiPalette)
        pal_layout.addWidget(self.pal_reset)
        pal_layout.addStretch()
        layout.addLayout(pal_layout)

        # Font picker
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self.viewer.font())
        self.font_combo.currentFontChanged.connect(
            lambda font: self.viewer.setFontFamily(font.family())
        )
        font_layout.addWidget(self.font_combo)
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)
        self.font_size.setValue(self.viewer.font().pointSize() or 10)
        self.font_size.valueChanged.connect(self.viewer.setFontSize)
        font_layout.addWidget(self.font_size)
        self.font_system = QPushButton("System font")
        self.font_system.setToolTip("Adopt the global QApplication font once")
        self.font_system.clicked.connect(self.use_system_font)
        font_layout.addWidget(self.font_system)
        font_layout.addStretch()
        layout.addLayout(font_layout)

        # Stats + bookmark bar
        extra_layout = QHBoxLayout()
        self.stats_label = QLabel("0 chars, 0 words, 0 lines")
        extra_layout.addWidget(self.stats_label)
        self.viewer.selectionChanged.connect(self.update_stats)
        self.bm_btn = QPushButton("Bookmark Line")
        self.bm_btn.setToolTip(
            "Bookmark / unbookmark current line (or click the gutter)"
        )
        self.bm_btn.clicked.connect(lambda: self.viewer.toggleBookmark())
        extra_layout.addWidget(self.bm_btn)
        self.bm_next = QPushButton("Next BM")
        self.bm_next.clicked.connect(lambda: self.viewer.gotoNextBookmark())
        extra_layout.addWidget(self.bm_next)
        self.bm_prev = QPushButton("Prev BM")
        self.bm_prev.clicked.connect(lambda: self.viewer.gotoPrevBookmark())
        extra_layout.addWidget(self.bm_prev)
        self.save_btn = QPushButton("Save Session")
        self.save_btn.clicked.connect(self.save_session)
        extra_layout.addWidget(self.save_btn)
        self.load_btn = QPushButton("Load Session")
        self.load_btn.clicked.connect(self.load_session)
        extra_layout.addWidget(self.load_btn)
        layout.addLayout(extra_layout)

        # Bookmark list view
        bm_layout = QHBoxLayout()
        bm_layout.addWidget(QLabel("Bookmarks:"))

        self.bm_list = QListWidget()
        self.bm_list.setMaximumHeight(70)
        self.bm_list.setToolTip(
            "All bookmarks — double-click to jump. Gutter click toggles."
        )
        self.bm_list.itemDoubleClicked.connect(self.goto_bookmark_item)
        bm_layout.addWidget(self.bm_list)
        layout.addLayout(bm_layout)
        self.viewer.bookmarksChanged.connect(self.refresh_bm_list)

        # Buttons
        button_layout = QHBoxLayout()

        btn = QPushButton("Test ANSI Colors")
        btn.clicked.connect(self.run_test)
        button_layout.addWidget(btn)

        self.stream_btn = QPushButton("Start Log Stream")
        self.stream_btn.setCheckable(True)
        self.stream_btn.clicked.connect(self.toggle_stream)
        button_layout.addWidget(self.stream_btn)

        self.pause_btn = QPushButton("Pause Stream")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self.toggle_pause)
        button_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear Output")
        self.clear_btn.clicked.connect(self.viewer.clear)
        button_layout.addWidget(self.clear_btn)

        self.zoom_in_btn = QPushButton("Zoom +")
        self.zoom_in_btn.clicked.connect(lambda: self.viewer.zoomIn(1))
        button_layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("Zoom -")
        self.zoom_out_btn.clicked.connect(lambda: self.viewer.zoomOut(1))
        button_layout.addWidget(self.zoom_out_btn)

        self.progress_btn = QPushButton("Test Progress Bar")
        self.progress_btn.clicked.connect(self.run_progress_test)
        button_layout.addWidget(self.progress_btn)

        self.burst_btn = QPushButton("Append 100k (async)")
        self.burst_btn.setToolTip("Non-blocking burst via appendAnsiTextAsync")
        self.burst_btn.clicked.connect(self.run_burst_test)
        button_layout.addWidget(self.burst_btn)

        layout.addLayout(button_layout)

        self.setCentralWidget(central)

        # Setup Logger Simulation
        self.logger = logging.getLogger("TestLogger")
        self.logger.setLevel(logging.DEBUG)
        handler = AnsiLogHandler(self.viewer)
        formatter = AnsiColorFormatter(
            "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.viewer.asyncAppendProgress.connect(self.show_burst_progress)
        self.viewer.asyncAppendFinished.connect(self.burst_finished)

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.generate_random_log)

    def do_search(self, *args):
        query = self.search_input.text()
        use_regex = self.regex_cb.isChecked()
        match_case = self.case_cb.isChecked()
        self.total_matches = self.viewer.highlight_search(query, use_regex, match_case)
        if self.total_matches > 0:
            self.match_label.setText(f"1/{self.total_matches}")
        else:
            self.match_label.setText("0/0")

    def do_filter(self, *args):
        query = self.filter_input.text()
        use_regex = self.regex_cb.isChecked()
        match_case = self.case_cb.isChecked()
        self.viewer.filter_search(query, use_regex, match_case)

    def update_match_label(self, current_index):
        if self.total_matches > 0:
            self.match_label.setText(f"{current_index}/{self.total_matches}")

    def run_test(self):
        for ansi_text in ANSI_SEQUENCES:
            # Isolate each sample: otherwise SGR state (bold/strike/...) bleeds
            # into all following lines, e.g. everything looks crossed-out.
            self.viewer.appendAnsiText(f"{ansi_text[0]}{ansi_text[1]}\x1b[0m\n")

    def run_progress_test(self):
        import time

        for i in range(0, 101, 20):
            self.viewer.appendAnsiText(f"\rDownloading... {i}%")
            QApplication.processEvents()
            time.sleep(0.05)
        self.viewer.appendAnsiText("\nDone. See https://example.com\n")

    def run_burst_test(self):
        self.burst_btn.setEnabled(False)
        self.burst_btn.setText("Appending...")
        lines = "".join(
            f"\x1b[32m[INFO]\x1b[0m burst line {i} https://example.com/{i}\n"
            for i in range(100000)
        )
        self.viewer.appendAnsiTextAsync(lines)

    def show_burst_progress(self, done: int, total: int):
        self.burst_btn.setText(f"Appending... {done}/{total}")

    def burst_finished(self):
        self.burst_btn.setText("Append 100k (async)")
        self.burst_btn.setEnabled(True)

    def toggle_stream(self, checked):
        if checked:
            self.viewer.beginNewStream()
            self.stream_btn.setText("Stop Log Stream")
            self.log_timer.start(500)
        else:
            self.stream_btn.setText("Start Log Stream")
            self.log_timer.stop()

    def toggle_pause(self, checked):
        if checked:
            self.pause_btn.setText("Resume Stream")
            self.viewer.pause_stream()
        else:
            self.pause_btn.setText("Pause Stream")
            self.viewer.resume_stream()

    def generate_random_log(self):
        level = random.choice(
            [
                logging.DEBUG,
                logging.INFO,
                logging.WARNING,
                logging.ERROR,
                logging.CRITICAL,
            ]
        )
        messages = [
            "Connection established successfully.",
            "Fetching data from endpoint '/api/v1/users'.",
            "Timeout occurred after 3000ms.",
            "Retrying connection attempt 3/5...",
            "Database constraint violation on table 'users'.",
            "Configuration file not found, creating default.",
            "Memory footprint currently at 45MB.",
        ]
        self.logger.log(level, random.choice(messages))

    def update_stats(self):
        s = self.viewer.selectionStats()
        self.stats_label.setText(
            f"{s['chars']} chars, {s['words']} words, {s['lines']} lines"
        )

    def refresh_bm_list(self, lines=None):
        self.bm_list.clear()
        for bno, preview in self.viewer.bookmarkedPreviews():
            self.bm_list.addItem(f"line {bno + 1}: {preview}")

    def goto_bookmark_item(self, item):
        try:
            line = int(item.text().split()[1].rstrip(":")) - 1
            cur = self.viewer.textCursor()
            cur.setPosition(self.viewer.document().findBlockByNumber(line).position())
            self.viewer.setTextCursor(cur)
            self.viewer.ensureCursorVisible()
        except Exception:
            pass

    def save_session(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "session.json", "JSON (*.json)"
        )
        if path:
            self.viewer.saveSession(path)

    def load_session(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "JSON (*.json)")
        if path:
            self.viewer.loadSession(path)

    def pick_default_color(self, which: str):
        from PySide6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        fg, bg = self.viewer.defaultColors()
        if which == "fg":
            self.viewer.setDefaultColors(color, bg)
        else:
            self.viewer.setDefaultColors(fg, color)
        self.match_theme_cb.setChecked(False)

    def use_system_font(self):
        self.viewer.useSystemFont()
        self.font_combo.setCurrentFont(self.viewer.font())
        self.font_size.setValue(self.viewer.font().pointSize() or 10)

    def pick_palette_color(self):
        from PySide6.QtWidgets import QColorDialog

        idx = self.pal_combo.currentIndex()
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.viewer.setAnsiPaletteColor(idx, color)
            self.viewer.appendAnsiText(
                f"\x1b[{30 + idx}mPalette {idx} preview\x1b[0m\n"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
