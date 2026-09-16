"""Tests for setter/getter symmetry and strict boolean parsing."""

import pytest


def test_boolean_getter_round_trip(viewer):
    assert viewer.isAutoScroll() is True
    viewer.setAutoScroll(False)
    assert viewer.isAutoScroll() is False

    assert viewer.isLineNumbersVisible() is True
    viewer.setLineNumbersVisible(False)
    assert viewer.isLineNumbersVisible() is False
    assert viewer.lineNumberAreaWidth() == 0

    assert viewer.isLinksEnabled() is True
    viewer.setLinksEnabled(False)
    assert viewer.isLinksEnabled() is False

    assert viewer.isLogLevelHighlighting() is False
    viewer.setLogLevelHighlighting(True)
    assert viewer.isLogLevelHighlighting() is True

    assert viewer.isSyntaxHighlighting() is False
    viewer.setSyntaxHighlighting(True)
    assert viewer.isSyntaxHighlighting() is True


@pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "off", "no", "n"])
def test_falsy_strings(viewer, value):
    viewer.setWordWrapEnabled(value)
    assert viewer.isWordWrapEnabled() is False
    viewer.setLineNumbersVisible(value)
    assert viewer.isLineNumbersVisible() is False
    assert viewer.lineNumberAreaWidth() == 0


@pytest.mark.parametrize("value", ["true", "True", "1", "on", "yes", "y"])
def test_truthy_strings(viewer, value):
    viewer.setWordWrapEnabled(value)
    assert viewer.isWordWrapEnabled() is True


def test_garbage_string_raises(viewer):
    with pytest.raises(ValueError):
        viewer.setWordWrapEnabled("maybe")


def test_non_string_behavior_unchanged(viewer):
    viewer.setWordWrapEnabled(0)
    assert viewer.isWordWrapEnabled() is False
    viewer.setWordWrapEnabled(1)
    assert viewer.isWordWrapEnabled() is True
    viewer.setWordWrapEnabled(None)
    assert viewer.isWordWrapEnabled() is False
