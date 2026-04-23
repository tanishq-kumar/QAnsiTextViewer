# QAnsiTextViewer
ANSI Text Viewer - QT Widget

## Roadmap

### Core / High-Value Features (Urgent)
- [x] **Search & Highlight**
  - [x] Find text (Ctrl+F)
  - [x] Highlight all matches
  - [x] Search with regex
  - [x] Find Next / Find Previous shortcuts
- [x] **Line Numbers**: Show line numbers on the left (very useful for logs)
- [x] **Auto-scroll Control**: Auto-scroll to bottom on new output (with option to freeze)
- [ ] **Fonts & Zoom**
  - Monospace font by default + size adjustment
  - Zoom In/Out (Ctrl + Mouse Wheel)
- [ ] **Word Wrap Toggle**: Option to enable/disable word wrap
- [ ] **Custom Context Menu**: Right-click menu: Copy, Select All, Clear, Save to File, etc.
- [x] **Clear Log**: Clear Button + Clear on Start
- [ ] **Timestamp Prefixing**: Automatically add `[HH:MM:SS]` to each new line
- [ ] **Log Level Highlighting**: Auto color `[ERROR]`, `[WARN]`, `[INFO]`, `[DEBUG]` differently

### Advanced / Nice-to-Have Features
- [ ] **Syntax Highlighting for Specific Logs**: JSON, Python traceback, CMake output, etc.
- [x] **Filter by Text**: Show only lines containing specific words
- [ ] **Bookmarks**: Bookmarked Lines
- [ ] **Export Log**: Save as `.txt`, `.html` (with colors), or `.md`
- [ ] **Copy Modes**: Copy with/without ANSI codes
- [ ] **Dark/Light Theme**: Auto Switch
- [ ] **Custom Color Palette**: User can change ANSI colors
- [ ] **Performance Optimizations**: Limit maximum lines (e.g. keep last 10,000 lines)
- [x] **Pause/Resume**: Output pause/resume button
- [ ] **Click-able Links**: URLs, file paths
- [ ] **Selection Statistics**: Line count, word count when text is selected
- [ ] **Highlight Current Line**
- [ ] **Support for `\r` Progress Bars**: Better handling of same-line updates
- [ ] **Save/Load Session**: Save current log content
