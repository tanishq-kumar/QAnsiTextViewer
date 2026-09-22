"""Snapshot of the public AnsiTextViewer API.

Guards against accidental renames, signature changes, or removed signals.
After an intentional API change, regenerate the baseline with:

    just api-snapshot

and commit the updated ``api_surface.txt`` alongside the change.
"""

import inspect
from pathlib import Path

BASELINE = Path(__file__).with_name("api_surface.txt")


def public_api():
    from ansi_text_viewer import AnsiTextViewer

    # Own attributes only: inherited Qt members belong to PySide6's
    # changelog, not ours — a Qt upgrade must not break this test.
    owned = set(vars(AnsiTextViewer))
    entries = []
    for name in sorted(owned):
        if name.startswith("_"):
            continue
        member = getattr(AnsiTextViewer, name)
        try:
            entries.append(f"{name}{inspect.signature(member)}")
        except (TypeError, ValueError):
            entries.append(f"{name}: {type(member).__name__}")
    return entries


def test_api_surface_matches_baseline():
    expected = BASELINE.read_text(encoding="utf-8").splitlines()
    assert public_api() == expected, (
        "Public API changed. If intentional, run `just api-snapshot` "
        "and commit the updated baseline."
    )


if __name__ == "__main__":
    BASELINE.write_text("\n".join(public_api()) + "\n", encoding="utf-8")
    print(f"wrote {BASELINE}")
