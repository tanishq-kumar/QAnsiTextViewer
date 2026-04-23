from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QTextEdit


class SearchHandler:
    def __init__(self, viewer):
        self.viewer = viewer
        self.search_highlight_color = QColor(255, 255, 0, 100)  # Translucent yellow
        self.active_search_color = QColor(255, 165, 0, 150)  # Translucent orange
        self.search_selections: list[QTextEdit.ExtraSelection] = []
        self.current_match_index = -1
        self.filter_query = ""
        self.filter_use_regex = False
        self.filter_match_case = False

    def highlight_search(
        self, query: str, use_regex: bool = False, match_case: bool = False
    ):
        if not query:
            self.clear_search_highlight()
            return 0

        selections: list[QTextEdit.ExtraSelection] = []
        doc: QTextDocument = self.viewer.document()
        cursor: QTextCursor = QTextCursor(doc)

        flags = QTextDocument.FindFlag(0)
        if match_case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        while True:
            if use_regex:
                regex = QRegularExpression(query)
                if match_case:
                    regex.setPatternOptions(
                        QRegularExpression.PatternOption.NoPatternOption
                    )
                else:
                    regex.setPatternOptions(
                        QRegularExpression.PatternOption.CaseInsensitiveOption
                    )
                cursor = doc.find(regex, cursor, flags)
            else:
                cursor = doc.find(query, cursor, flags)

            if cursor.isNull():
                break

            selection = QTextEdit.ExtraSelection()

            selection.cursor = cursor
            selections.append(selection)

        self.search_selections = selections
        self.current_match_index = 0 if selections else -1
        self.__update_search_highlights()

        return len(selections)

    def __update_search_highlights(self):
        if not self.search_selections:
            self.viewer.setExtraSelections([])
            return

        selections = []
        for i, selection in enumerate(self.search_selections):
            s = QTextEdit.ExtraSelection()
            s.cursor = selection.cursor
            fmt = QTextCharFormat()
            if i == self.current_match_index:
                fmt.setBackground(self.active_search_color)
            else:
                fmt.setBackground(self.search_highlight_color)
            s.format = fmt
            selections.append(s)

        self.viewer.setExtraSelections(selections)

        if 0 <= self.current_match_index < len(self.search_selections):
            active_cursor = self.search_selections[self.current_match_index].cursor
            self.viewer.setTextCursor(active_cursor)
            self.viewer.ensureCursorVisible()

    def next_match(self):
        if not self.search_selections:
            return 0
        self.current_match_index = (self.current_match_index + 1) % len(
            self.search_selections
        )
        self.__update_search_highlights()
        return self.current_match_index + 1

    def prev_match(self):
        if not self.search_selections:
            return 0
        if self.current_match_index <= 0:
            self.current_match_index = len(self.search_selections) - 1
        else:
            self.current_match_index -= 1
        self.__update_search_highlights()
        return self.current_match_index + 1

    def clear_search_highlight(self):
        self.search_selections = []
        self.current_match_index = -1
        self.viewer.setExtraSelections([])

    def setSearchHighlightColor(self, color: QColor, active_color: QColor = None):
        self.search_highlight_color = color
        if active_color:
            self.active_search_color = active_color

    def apply_filter(self, query: str, use_regex: bool = False, match_case: bool = False):
        self.filter_query = query
        self.filter_use_regex = use_regex
        self.filter_match_case = match_case
        
        doc = self.viewer.document()
        self.filter_blocks(doc.firstBlock())
        
        doc.documentLayout().requestUpdate()
        self.viewer.viewport().update()

    def filter_blocks(self, start_block):
        if not self.filter_query:
            while start_block.isValid():
                start_block.setVisible(True)
                start_block = start_block.next()
            return

        import re
        pattern = None
        query = self.filter_query
        if self.filter_use_regex:
            flags = 0 if self.filter_match_case else re.IGNORECASE
            try:
                pattern = re.compile(query, flags)
            except re.error:
                pattern = re.compile(re.escape(query), flags)
        else:
            if not self.filter_match_case:
                query = query.lower()

        while start_block.isValid():
            text = start_block.text()
            if self.filter_use_regex:
                match = bool(pattern.search(text))
            else:
                match = query in (text if self.filter_match_case else text.lower())
            
            start_block.setVisible(match)
            start_block = start_block.next()

    def update_new_blocks(self, start_block_number: int):
        if not self.filter_query:
            return
        doc = self.viewer.document()
        block = doc.findBlockByNumber(start_block_number)
        if block.isValid():
            self.filter_blocks(block)
            doc.documentLayout().requestUpdate()
