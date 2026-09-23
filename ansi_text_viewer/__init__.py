"""Public API for QAnsiTextViewer (Qt for Python ANSI log viewer).

The widget import is lazy (PEP 562) so that importing submodules such as
``ansi_text_viewer.ansi_escape_handler`` — which is deliberately Qt-free —
never pulls in Qt as a side effect. Fuzz targets rely on this.
"""

__all__ = ["AnsiTextViewer"]


def __getattr__(name: str):
    """Lazily expose the widget class on first attribute access."""
    if name == "AnsiTextViewer":
        from ansi_text_viewer.ansi_text_viewer import AnsiTextViewer

        return AnsiTextViewer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
