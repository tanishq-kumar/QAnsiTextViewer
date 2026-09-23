"""ClusterFuzzLite target: the ANSI escape parser must not crash.

Mirrors tests/test_parser_properties.py invariants at libFuzzer scale.
Run in CI via .github/workflows/cflite-*.yml; needs no display because the
parser only uses Qt value types (QColor/QTextCharFormat), never widgets.
"""

import sys

import atheris

from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler


def TestOneInput(data: bytes) -> None:
    """Fuzz the parser: no crashes, no ESC leaks in text payloads."""
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 4096))
    actions = AnsiEscapeHandler().parse(text)
    for action in actions:
        kind, *rest = action
        if kind == "text":
            assert "\x1b" not in rest[0]


def main() -> None:
    """Wire the target into libFuzzer via atheris."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
