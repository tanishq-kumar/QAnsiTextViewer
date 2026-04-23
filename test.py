import sys
import logging
import random
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QCheckBox,
    QLabel,
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
        logging.DEBUG: "\x1b[36m",    # Cyan
        logging.INFO: "\x1b[32m",     # Green
        logging.WARNING: "\x1b[33m",  # Yellow
        logging.ERROR: "\x1b[31m",    # Red
        logging.CRITICAL: "\x1b[1;31m"# Bold Red
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

        # Search Controls UI
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Highlight Search...")
        self.search_input.textChanged.connect(self.do_search)

        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.clicked.connect(lambda: self.update_match_label(self.viewer.prev_match()))

        self.btn_next = QPushButton(">")
        self.btn_next.setFixedWidth(30)
        self.btn_next.clicked.connect(lambda: self.update_match_label(self.viewer.next_match()))

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

        viewer_controls.addStretch()
        layout.addLayout(viewer_controls)

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
        
        layout.addLayout(button_layout)
        
        self.setCentralWidget(central)

        # Setup Logger Simulation
        self.logger = logging.getLogger("TestLogger")
        self.logger.setLevel(logging.DEBUG)
        handler = AnsiLogHandler(self.viewer)
        formatter = AnsiColorFormatter("%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

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
            self.viewer.appendAnsiText(f"{ansi_text[0]}{ansi_text[1]}\n")

    def toggle_stream(self, checked):
        if checked:
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
        level = random.choice([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL])
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
