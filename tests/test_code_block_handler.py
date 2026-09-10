"""
test_code_block_handler.py — Unit test untuk code_block_handler.
"""

from __future__ import annotations

import pytest

from src.handlers import code_block_handler


def make_block(content: str, lang: str = "") -> str:
    """Helper: bungkus content dalam fenced block."""
    fence = f"```{lang}\n" if lang else "```\n"
    return f"{fence}{content}```\n"


class TestCodeBlockHandlerEnv:
    """Test masking untuk env-style code block."""

    def test_password_key_is_masked(self):
        raw = make_block("DB_PASSWORD=mySecret123\n", lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert "mySecret123" not in result
        assert "DB_PASSWORD" in result  # key dipertahankan

    def test_api_key_env_masked(self):
        raw = make_block("API_KEY=AbCdEfGhIjKlMnOpQrSt\n", lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert "AbCdEfGhIjKlMnOpQrSt" not in result

    def test_non_sensitive_key_not_masked(self):
        raw = make_block("APP_NAME=MyApp\nAPP_VERSION=1.0\n", lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert "MyApp" in result
        assert "1.0" in result

    def test_mixed_env_file(self):
        content = (
            "APP_NAME=MyService\n"
            "DB_HOST=localhost\n"
            "DB_PASSWORD=s3cr3t\n"
            "DB_PORT=5432\n"
            "API_KEY=AbCdEfGhIjKlMnOpQrSt\n"
        )
        raw = make_block(content, lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert "MyService" in result
        assert "s3cr3t" not in result
        assert "AbCdEfGhIjKlMnOpQrSt" not in result

    def test_fence_preserved(self):
        raw = make_block("SECRET=abc\n", lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert result.startswith("```env")
        assert "```" in result[-5:]


class TestCodeBlockHandlerYAML:
    def test_yaml_password_masked(self):
        content = "database:\n  password: myS3cr3t\n  host: localhost\n"
        raw = make_block(content, lang="yaml")
        result = code_block_handler.mask(raw, lang="yaml")
        assert "myS3cr3t" not in result

    def test_yaml_non_sensitive_preserved(self):
        content = "app:\n  name: MyApp\n  version: 1.0\n"
        raw = make_block(content, lang="yaml")
        result = code_block_handler.mask(raw, lang="yaml")
        assert "MyApp" in result
        assert "1.0" in result


class TestCodeBlockHandlerJSON:
    def test_json_password_masked(self):
        content = '{\n  "password": "mySecret",\n  "host": "localhost"\n}\n'
        raw = make_block(content, lang="json")
        result = code_block_handler.mask(raw, lang="json")
        assert "mySecret" not in result

    def test_json_non_sensitive_preserved(self):
        content = '{\n  "app_name": "MyService",\n  "version": "1.0"\n}\n'
        raw = make_block(content, lang="json")
        result = code_block_handler.mask(raw, lang="json")
        assert "MyService" in result


class TestCodeBlockHandlerGeneric:
    def test_credential_regex_in_python_block(self):
        content = "# config.py\npassword = 'MySuperSecret'\n"
        raw = make_block(content, lang="python")
        result = code_block_handler.mask(raw, lang="python")
        assert "MySuperSecret" not in result

    def test_db_uri_in_generic_block(self):
        content = "DB_URL = postgresql://user:pass@host:5432/db\n"
        raw = make_block(content, lang="")
        result = code_block_handler.mask(raw, lang="")
        assert "pass" not in result.lower() or "postgresql" not in result

    def test_empty_block(self):
        raw = make_block("", lang="env")
        result = code_block_handler.mask(raw, lang="env")
        assert "```" in result  # fence dipertahankan

    def test_non_sensitive_code_preserved(self):
        content = "def hello():\n    return 'world'\n"
        raw = make_block(content, lang="python")
        result = code_block_handler.mask(raw, lang="python")
        assert "def hello" in result
        assert "world" in result
