"""
test_replace_engine.py — Unit test untuk replace_engine.

Menguji dua risiko yang eksplisit disebut di plan.md:
- Risiko #1: value pendek/generic di-skip.
- Risiko #2: replace urut DESC by length (substring tidak rusak duluan).
"""

from __future__ import annotations

from types import SimpleNamespace

from src.replace_engine import collect_literal_values, replace_into_original


def _result(start: int, end: int):
    """Stand-in ringan untuk RecognizerResult — cuma butuh .start/.end."""
    return SimpleNamespace(start=start, end=end)


class TestCollectLiteralValues:
    def test_basic_extraction(self):
        text = "password: mySecret123"
        results = [_result(10, 22)]
        values = collect_literal_values(text, results)
        assert values == ["mySecret123"]

    def test_dedup(self):
        text = "mySecret mySecret"
        results = [_result(0, 8), _result(9, 17)]
        values = collect_literal_values(text, results)
        assert values == ["mySecret"]

    def test_short_value_skipped(self):
        """Risiko #1 — value < 4 karakter di-skip."""
        text = "pin: 12"
        results = [_result(5, 7)]  # "12" — 2 karakter
        values = collect_literal_values(text, results)
        assert values == []

    def test_min_length_boundary(self):
        text = "code: 1234"
        results = [_result(6, 10)]  # "1234" — persis 4 karakter, harus lolos
        values = collect_literal_values(text, results)
        assert values == ["1234"]

    def test_sorted_desc_by_length(self):
        """Risiko #2 — value terpanjang duluan."""
        text = "admin admin_prod"
        results = [_result(0, 5), _result(6, 17)]  # "admin", "admin_prod"
        values = collect_literal_values(text, results)
        assert values == ["admin_prod", "admin"]


class TestReplaceIntoOriginal:
    def test_basic_replace(self):
        raw = "password=mySecret123"
        result = replace_into_original(raw, ["mySecret123"])
        assert result == "password=<REDACTED>"

    def test_value_not_found_is_noop(self):
        """Value yang tidak ada di raw markdown dilewati diam-diam, dokumen lain tidak terpengaruh."""
        raw = "hello world"
        result = replace_into_original(raw, ["notpresent"])
        assert result == "hello world"

    def test_substring_not_corrupted_when_longer_value_replaced_first(self):
        """Risiko #2 — 'admin_prod' diganti utuh sebelum 'admin' sempat merusaknya."""
        raw = "user: admin_prod"
        result = replace_into_original(raw, ["admin_prod", "admin"])
        assert result == "user: <REDACTED>"
        assert "REDACTED_prod" not in result

    def test_custom_placeholder(self):
        raw = "token=abcdef123456"
        result = replace_into_original(raw, ["abcdef123456"], placeholder="<API_KEY>")
        assert result == "token=<API_KEY>"

    def test_replaces_all_occurrences(self):
        raw = "secret=abc123 and again secret=abc123"
        result = replace_into_original(raw, ["abc123"])
        assert result.count("<REDACTED>") == 2
        assert "abc123" not in result
