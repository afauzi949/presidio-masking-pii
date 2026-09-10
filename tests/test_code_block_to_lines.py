"""
test_code_block_to_lines.py — Unit test untuk reconstruction.code_block_to_lines.

Menguji hasil normalisasi (bukan masking — masking terjadi belakangan lewat
Presidio + replace_engine, lihat test_masker.py).
"""

from __future__ import annotations

from src.reconstruction.code_block_to_lines import code_block_to_lines


def make_block(content: str, lang: str = "") -> str:
    fence = f"```{lang}\n" if lang else "```\n"
    return f"{fence}{content}```\n"


class TestCodeBlockToLinesEnv:
    def test_fence_removed(self):
        raw = make_block("DB_PASSWORD=mySecret123\n", lang="env")
        result = code_block_to_lines(raw, lang="env")
        assert "```" not in result

    def test_content_preserved(self):
        raw = make_block("DB_PASSWORD=mySecret123\n", lang="env")
        result = code_block_to_lines(raw, lang="env")
        assert "DB_PASSWORD=mySecret123" in result

    def test_multiple_lines_preserved(self):
        content = "APP_NAME=MyService\nDB_PASSWORD=s3cr3t\n"
        raw = make_block(content, lang="env")
        result = code_block_to_lines(raw, lang="env")
        assert "APP_NAME=MyService" in result
        assert "DB_PASSWORD=s3cr3t" in result


class TestCodeBlockToLinesJSON:
    def test_json_flattened_to_key_value_lines(self):
        content = '{\n  "password": "mySecret",\n  "host": "localhost"\n}\n'
        raw = make_block(content, lang="json")
        result = code_block_to_lines(raw, lang="json")
        assert "password: mySecret" in result
        assert "host: localhost" in result
        # Sintaks JSON asli (kutip, kurung kurawal) sudah tidak ada
        assert "{" not in result
        assert '"' not in result

    def test_invalid_json_falls_back_to_raw_content(self):
        content = "{not valid json,,,\n"
        raw = make_block(content, lang="json")
        result = code_block_to_lines(raw, lang="json")
        assert "not valid json" in result


class TestCodeBlockToLinesGeneric:
    def test_python_code_content_preserved(self):
        content = "# config.py\npassword = 'MySuperSecret'\n"
        raw = make_block(content, lang="python")
        result = code_block_to_lines(raw, lang="python")
        assert "MySuperSecret" in result

    def test_no_lang_content_preserved(self):
        content = "DB_URL = postgresql://user:pass@host:5432/db\n"
        raw = make_block(content, lang="")
        result = code_block_to_lines(raw, lang="")
        assert "postgresql://user:pass@host:5432/db" in result

    def test_empty_block(self):
        raw = make_block("", lang="env")
        result = code_block_to_lines(raw, lang="env")
        assert result == ""

    def test_multiline_kv_joined(self):
        """code_block_to_lines memanggil join_multiline_kv — label/value baris
        terpisah harus tergabung."""
        content = "Password:\nVpn@ccess2024!\n"
        raw = make_block(content, lang="conf")
        result = code_block_to_lines(raw, lang="conf")
        assert "Password: Vpn@ccess2024!" in result
