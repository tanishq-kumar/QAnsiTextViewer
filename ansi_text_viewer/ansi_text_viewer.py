from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler
from ansi_text_viewer.line_number_area import LineNumberArea
from ansi_text_viewer.search_handler import SearchHandler
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter


class AnsiTextViewer(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.__ansi_escape_handler = AnsiEscapeHandler()
        self.__search_handler = SearchHandler(self)

        # Line number area setup
        self.__line_numbers_visible = True
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth(0)

        # Auto-scroll state
        self.__auto_scroll = True
        
        # Stream buffering state
        self.__is_paused = False
        self.__stream_buffer = []

    def setAutoScroll(self, enabled: bool):
        self.__auto_scroll = enabled

    def setLineNumbersVisible(self, visible: bool):
        self.__line_numbers_visible = visible
        self.lineNumberArea.setVisible(visible)
        self.updateLineNumberAreaWidth(0)

    def setSearchHighlightColor(self, color: QColor):
        self.__search_handler.setSearchHighlightColor(color)

    def highlight_search(
        self, query: str, use_regex: bool = False, match_case: bool = False
    ):
        return self.__search_handler.highlight_search(query, use_regex, match_case)

    def filter_search(self, query: str, use_regex: bool = False, match_case: bool = False):
        self.__search_handler.apply_filter(query, use_regex, match_case)

    def next_match(self):
        return self.__search_handler.next_match()

    def prev_match(self):
        return self.__search_handler.prev_match()

    def clear_search_highlight(self):
        self.__search_handler.clear_search_highlight()

    def lineNumberAreaWidth(self):
        if not self.__line_numbers_visible:
            return 0
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect: QRect, dy: int):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(
                0, rect.y(), self.lineNumberArea.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        if not self.__line_numbers_visible:
            return

        painter = QPainter(self.lineNumberArea)
        painter.setFont(self.font())
        painter.fillRect(event.rect(), QColor(240, 240, 240))  # Light background

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.darkGray)
                painter.drawText(
                    0,
                    top,
                    self.lineNumberArea.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def __execute_actions(self, actions, cursor):
        for action in actions:
            cmd = action[0]
            if cmd == "text":
                cursor.insertText(action[1], action[2])
            elif cmd == "cursor_up":
                for _ in range(action[1]):
                    cursor.movePosition(cursor.MoveOperation.Up)
            elif cmd == "cursor_down":
                for _ in range(action[1]):
                    cursor.movePosition(cursor.MoveOperation.Down)
            elif cmd == "cursor_forward":
                for _ in range(action[1]):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "cursor_back":
                for _ in range(action[1]):
                    cursor.movePosition(cursor.MoveOperation.Left)
            elif cmd == "cursor_col":
                cursor.movePosition(cursor.MoveOperation.StartOfLine)
                for _ in range(action[1] - 1):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "cursor_pos":
                cursor.movePosition(cursor.MoveOperation.Start)
                for _ in range(action[1] - 1):
                    cursor.movePosition(cursor.MoveOperation.Down)
                for _ in range(action[2] - 1):
                    cursor.movePosition(cursor.MoveOperation.Right)
            elif cmd == "erase_screen":
                mode = action[1]
                if mode == 2:
                    self.clear()
                    cursor = self.textCursor()
                elif mode == 0:
                    cursor.movePosition(
                        cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 1:
                    cursor.movePosition(
                        cursor.MoveOperation.Start, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
            elif cmd == "erase_line":
                mode = action[1]
                if mode == 2:
                    cursor.movePosition(cursor.MoveOperation.StartOfLine)
                    cursor.movePosition(
                        cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 0:
                    cursor.movePosition(
                        cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
                elif mode == 1:
                    cursor.movePosition(
                        cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor
                    )
                    cursor.removeSelectedText()
            elif cmd == "hide_cursor":
                self.setCursorWidth(0)
            elif cmd == "show_cursor":
                self.setCursorWidth(1)
        self.setTextCursor(cursor)

    def pause_stream(self):
        self.__is_paused = True

    def resume_stream(self):
        self.__is_paused = False
        if self.__stream_buffer:
            buffer_text = "".join(self.__stream_buffer)
            self.__stream_buffer.clear()
            self._appendAnsiTextInternal(buffer_text)

    def appendAnsiText(self, text: str):
        if self.__is_paused:
            self.__stream_buffer.append(text)
        else:
            self._appendAnsiTextInternal(text)

    def _appendAnsiTextInternal(self, text: str):
        old_count = max(0, self.document().blockCount() - 1)
        actions = self.__ansi_escape_handler.parse(text)
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.__execute_actions(actions, cursor)
        self.__search_handler.update_new_blocks(old_count)
        if self.__auto_scroll:
            self.ensureCursorVisible()

    def setAnsiText(self, text: str):
        self.clear()
        self.appendAnsiText(text)

    def insertAnsiText(self, text: str):
        actions = self.__ansi_escape_handler.parse(text)
        cursor = self.textCursor()
        self.__execute_actions(actions, cursor)

    def clear(self):
        super().clear()
        self.__ansi_escape_handler.reset()
        self.clear_search_highlight()
