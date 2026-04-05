"""Tests for synthesis dict summarization used in persona evidence_summary."""

import json

from app.personas.designer import _has_research_results, summarize_synthesis_dict


def test_summarize_synthesis_dict_small_dict_round_trips():
    syn = {"a": 1, "b": "hello"}
    out = summarize_synthesis_dict(syn)
    assert len(out) <= 4000
    assert '"a"' in out
    assert "hello" in out
    parsed = json.loads(out)
    assert parsed == syn


def test_summarize_synthesis_dict_bounds_huge_strings():
    syn = {"k": "x" * 50_000, "nested": {"inner": ["y" * 10_000]}}
    out = summarize_synthesis_dict(syn)
    assert len(out) <= 4000


def test_summarize_deep_nesting_truncates_at_depth_cap():
    """Depth > 40 yields literal '<truncated>' leaves (recursive shrink guard)."""
    x: dict | str = "leaf"
    for _ in range(41):
        x = {"L": x}
    out = summarize_synthesis_dict(x, max_chars=8000)
    assert "<truncated>" in out
    parsed = json.loads(out)
    cur: object = parsed
    for _ in range(41):
        assert isinstance(cur, dict)
        assert "L" in cur
        cur = cur["L"]
    assert cur == "<truncated>"


def test_summarize_unicode_large_string_truncates_without_mojibake():
    """Long Unicode strings truncate on codepoint boundaries; JSON is valid UTF-8."""
    text = "あ" * 12_000 + "β" * 12_000 + "🙂" * 500
    syn = {"label": text}
    out = summarize_synthesis_dict(syn, max_chars=4000)
    assert len(out) <= 4000
    assert "<truncated>" in out
    parsed = json.loads(out)
    inner = parsed["label"]
    assert isinstance(inner, str)
    assert inner.endswith("<truncated>")
    assert "あ" in inner or "β" in inner or "🙂" in inner
    # test_summarize_unicode_large_string_truncates_without_mojibake: inner must
    # round-trip UTF-8 (summarize_synthesis_dict output is decodable, not mojibake)
    assert inner.encode("utf-8").decode("utf-8") == inner


def test_summarize_large_list_and_many_dict_keys_reduces():
    """Exercises max_list / max_dict_keys truncation and shrink-loop halving."""
    syn = {
        "wide": {str(i): f"v{i}" for i in range(120)},
        "long_list": list(range(500)),
    }
    out = summarize_synthesis_dict(syn, max_chars=4000)
    assert len(out) <= 4000
    assert "<truncated>" in out
    parsed = json.loads(out)
    assert "_truncated" in parsed["wide"] or len(parsed["wide"]) <= 35
    wl = parsed["long_list"]
    assert isinstance(wl, list)
    assert "<truncated>" in wl or len(wl) <= 45


def test_summarize_tuple_set_and_custom_object_serializes():
    class _CustomObj:
        def __str__(self) -> str:
            return "custom-obj"

    syn = {
        "t": (1, 2, "three"),
        "s": {1, 2, 3},
        "o": _CustomObj(),
    }
    out = summarize_synthesis_dict(syn, max_chars=4000)
    parsed = json.loads(out)
    assert parsed["t"] == [1, 2, "three"]
    assert sorted(parsed["s"]) == [1, 2, 3]
    assert parsed["o"] == "custom-obj"


def test_summarize_fallback_binary_search_when_shrink_never_fits():
    """After 24 shrink iterations, raw JSON preview path fits max_chars (binary search).

    The minimum fallback envelope is ~35 chars (empty preview); max_chars must exceed
    that for a non-vacuous preview. Adversarial wide nested dict keeps len(shrunk JSON)
    above a tight cap so the preview branch runs.
    """
    syn = {str(i): {str(j): "z" * 200 for j in range(80)} for i in range(80)}
    max_chars = 100
    out = summarize_synthesis_dict(syn, max_chars=max_chars)
    assert len(out) <= max_chars
    parsed = json.loads(out)
    assert parsed["_truncated"] is True
    assert "preview" in parsed
    raw = json.dumps(syn, ensure_ascii=False)
    assert parsed["preview"] == raw[: len(parsed["preview"])]
    assert parsed["preview"] in raw


def test_has_research_results_raw_hits():
    assert _has_research_results({"raw_results": [{"title": "A", "url": "u"}]})


def test_has_research_results_synthesis_string():
    assert _has_research_results({"raw_results": [], "synthesis": "Some findings."})


def test_has_research_results_synthesis_dict():
    assert _has_research_results({"synthesis": {"role": "CEO"}})


def test_has_research_results_empty():
    assert not _has_research_results({})
    assert not _has_research_results({"raw_results": [], "synthesis": {}})
    assert not _has_research_results({"raw_results": [], "synthesis": "  \n"})


def test_summarize_synthesis_dict_fallback_when_still_too_large():
    # Adversarial: very wide dict so recursive shrink may not converge under limit
    syn = {str(i): {str(j): "z" * 200 for j in range(80)} for i in range(80)}
    out = summarize_synthesis_dict(syn, max_chars=4000)
    assert len(out) <= 4000
    assert "_truncated" in out or "<truncated>" in out
