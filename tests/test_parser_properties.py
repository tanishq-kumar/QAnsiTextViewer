"""Property tests for the ANSI escape parser.

Same invariants as the ClusterFuzzLite target (``fuzz/fuzz_ansi.py``):
hostile input must never crash parsing, and plain-text payloads must never
leak escape characters. Hypothesis covers the everyday PR loop; libFuzzer
covers the deep end on a schedule.
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ansi_text_viewer.ansi_escape_handler import AnsiEscapeHandler

ESC = "\x1b"
# Escape-heavy alphabet plus ordinary text: biased to find parser bugs fast.
ansi_text = st.text(
    alphabet=st.sampled_from(list(f"{ESC}[]0123456789;?mABCDEFGHJKSTXsu \nabcxyz")),
    max_size=300,
)
any_text = st.text(max_size=200)


def projection(actions):
    """Comparable shape of parse output (formats excluded)."""
    shape = []
    for action in actions:
        kind, *rest = action
        if kind == "text":
            shape.append((kind, rest[0]))
        else:
            shape.append((kind, *rest))
    return shape


@given(ansi_text)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_parse_never_raises(payload):
    AnsiEscapeHandler().parse(payload)


@given(any_text)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_text_payloads_contain_no_esc(payload):
    for kind, *rest in projection(AnsiEscapeHandler().parse(payload)):
        if kind == "text":
            assert ESC not in rest[0]


@given(ansi_text)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_parse_is_deterministic(payload):
    first = projection(AnsiEscapeHandler().parse(payload))
    second = projection(AnsiEscapeHandler().parse(payload))
    assert first == second
