"""
test_table_to_sentence.py — Unit test untuk reconstruction.table_to_sentence.

Menguji representasi teks yang dihasilkan (bukan masking — masking terjadi
belakangan lewat Presidio + replace_engine, lihat test_masker.py).
"""

from __future__ import annotations

from src.reconstruction.table_to_sentence import table_to_sentence


class TestTableToSentence:
    def test_empty_table(self):
        assert table_to_sentence("") == ""

    def test_header_and_value_represented(self):
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | mySecret |\n"
        )
        result = table_to_sentence(raw)
        assert "Service: DB" in result
        assert "Password: mySecret" in result

    def test_no_period_appended_to_value(self):
        """Value tidak boleh diikuti '.' — kalau ada, replace-balik ke raw
        markdown bisa gagal karena raw cell tidak punya titik itu."""
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | mySecret |\n"
        )
        result = table_to_sentence(raw)
        assert "mySecret." not in result
        assert "mySecret\n" in result or result.endswith("mySecret")

    def test_multiple_rows_separated(self):
        raw = (
            "| Name | Email |\n"
            "|------|-------|\n"
            "| Alice | alice@example.com |\n"
            "| Bob | bob@example.com |\n"
        )
        result = table_to_sentence(raw)
        assert "Name: Alice" in result
        assert "Email: alice@example.com" in result
        assert "Name: Bob" in result
        assert "Email: bob@example.com" in result

    def test_empty_cell_not_represented(self):
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      |          |\n"
        )
        result = table_to_sentence(raw)
        assert "Service: DB" in result
        assert "Password:" not in result

    def test_header_row_and_separator_not_treated_as_data(self):
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | mySecret |\n"
        )
        result = table_to_sentence(raw)
        assert "---" not in result

    def test_no_data_rows_returns_empty(self):
        """Cuma satu baris (tanpa separator/data row) — tidak ada row untuk direpresentasikan."""
        assert table_to_sentence("just some text, not a table") == ""
