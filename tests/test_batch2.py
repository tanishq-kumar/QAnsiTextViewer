from PySide6.QtCore import Qt


def test_clear_on_start_api(viewer):
    assert viewer.isClearOnStart() is False
    viewer.setAnsiText("old\n")
    viewer.setClearOnStart(True)
    assert viewer.isClearOnStart() is True
    viewer.beginNewStream()
    assert viewer.toPlainText().strip() == ""
    viewer.setClearOnStart(False)
    viewer.appendAnsiText("kept\n")
    viewer.beginNewStream()
    assert "kept" in viewer.toPlainText()


def test_shortcuts_are_app_wide(viewer):
    _ctx = Qt.ShortcutContext.ApplicationShortcut
    assert viewer._AnsiTextViewer__sc_find.context() == _ctx
    assert viewer._AnsiTextViewer__sc_next.context() == _ctx
    assert viewer._AnsiTextViewer__sc_prev.context() == _ctx


def test_theme_requested_auto(viewer):
    viewer.setTheme("auto")
    assert viewer.themeRequested() == "auto"
    assert viewer.theme() in ("light", "dark")
    viewer.setTheme("dark")
    assert viewer.themeRequested() == "dark"
    viewer.setTheme("light")


def test_cmake_syntax_highlight(viewer):
    viewer.setSyntaxHighlighting(True)
    viewer.appendAnsiText("CMake Error at CMakeLists.txt:10\n")
    viewer.appendAnsiText("-- Configuring done\n")
    viewer.appendAnsiText("[ 50%] Built target myapp\n")
    text = viewer.toPlainText()
    assert "CMake Error" in text
    assert "Configuring done" in text
    assert "Built target" in text
    viewer.setSyntaxHighlighting(False)


def test_main_entry_importable():
    import main

    assert callable(main.main)


def test_justfile_syntax_highlight(viewer):
    viewer.setSyntaxHighlighting(True)
    viewer.appendAnsiText("test: build lint\n")
    viewer.appendAnsiText('NAME := "demo"\n')
    viewer.appendAnsiText("echo {{NAME}}\n")
    viewer.appendAnsiText("# a comment\n")
    text = viewer.toPlainText()
    assert "test:" in text
    assert "NAME" in text
    assert "{{NAME}}" in text
    viewer.setSyntaxHighlighting(False)
