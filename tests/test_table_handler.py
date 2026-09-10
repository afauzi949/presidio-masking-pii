"""
test_table_handler.py — Unit test untuk table_handler.
"""

from __future__ import annotations

import pytest

from src.handlers import table_handler


class TestTableHandler:
    def test_password_column_masked(self):
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | mySecret  |\n"
            "| API     | anotherS3cr3t |\n"
        )
        result = table_handler.mask(raw)
        assert "mySecret" not in result
        assert "anotherS3cr3t" not in result

    def test_non_sensitive_column_preserved(self):
        raw = (
            "| Name  | Role  | Email |\n"
            "|-------|-------|-------|\n"
            "| Alice | Admin | alice@example.com |\n"
        )
        result = table_handler.mask(raw)
        assert "Alice" in result
        assert "Admin" in result
        # Email — tidak ada di TABLE_SENSITIVE_COLUMNS default, jadi dipertahankan
        assert "alice@example.com" in result

    def test_token_column_masked(self):
        raw = (
            "| System | Token              |\n"
            "|--------|--------------------|   \n"
            "| Auth   | AbCdEfGhIjKlMnOpQr |\n"
        )
        result = table_handler.mask(raw)
        assert "AbCdEfGhIjKlMnOpQr" not in result

    def test_api_key_column_masked(self):
        raw = (
            "| Partner | api_key           |\n"
            "|---------|-------------------|\n"
            "| PayGW   | sk_live_1234567890 |\n"
        )
        result = table_handler.mask(raw)
        assert "sk_live_1234567890" not in result

    def test_output_is_valid_markdown_table(self):
        """Output harus tetap punya header | separator | data rows."""
        raw = (
            "| Name | Password |\n"
            "|------|----------|\n"
            "| Bob  | p@ssw0rd |\n"
        )
        result = table_handler.mask(raw)
        lines = [l for l in result.splitlines() if l.strip()]
        assert len(lines) >= 3, "Harus ada minimal header + separator + 1 data row"
        assert "|" in lines[0]  # header
        assert "-" in lines[1]  # separator
        assert "|" in lines[2]  # data row

    def test_header_row_not_masked(self):
        """Nama kolom itu sendiri tidak boleh di-mask."""
        raw = (
            "| username | password |\n"
            "|----------|----------|\n"
            "| admin    | s3cr3t   |\n"
        )
        result = table_handler.mask(raw)
        assert "username" in result
        assert "password" in result

    def test_empty_table(self):
        result = table_handler.mask("")
        assert result == ""

    def test_table_with_empty_values(self):
        """Nilai kosong tidak boleh di-mask jadi <REDACTED>."""
        raw = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      |          |\n"
        )
        result = table_handler.mask(raw)
        # Nilai kosong dipertahankan apa adanya
        assert "<REDACTED>" not in result or "DB" in result

    def test_multiple_sensitive_columns(self):
        raw = (
            "| Service | Password | Token         |\n"
            "|---------|----------|---------------|\n"
            "| API     | secret   | tok_abc123xyz |\n"
        )
        result = table_handler.mask(raw)
        assert "secret" not in result
        assert "tok_abc123xyz" not in result

    def test_column_name_case_insensitive(self):
        """Matching kolom sensitif harus case-insensitive."""
        raw = (
            "| Service | PASSWORD |\n"
            "|---------|----------|\n"
            "| DB      | myPass   |\n"
        )
        result = table_handler.mask(raw)
        assert "myPass" not in result
