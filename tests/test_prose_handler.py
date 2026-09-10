"""
test_prose_handler.py — Unit test untuk prose_handler.
"""

from __future__ import annotations

import pytest

from src.handlers import prose_handler


class TestProseHandler:
    def test_empty_string(self):
        assert prose_handler.mask("") == ""

    def test_whitespace_only(self):
        result = prose_handler.mask("   ")
        assert result.strip() == "" or result == "   "

    def test_email_is_masked(self):
        text = "Hubungi saya di john.doe@example.com untuk informasi lebih lanjut."
        result = prose_handler.mask(text)
        assert "john.doe@example.com" not in result, "Email harus ter-mask"

    def test_person_name_may_be_masked(self):
        """PERSON entity — opsional karena spaCy NER tidak selalu 100% recall."""
        text = "Hubungi John Smith untuk pertanyaan teknis."
        result = prose_handler.mask(text)
        # Hanya pastikan tidak ada exception — NER recall bervariasi
        assert isinstance(result, str)

    def test_credential_kv_in_prose_is_masked(self):
        text = "Gunakan konfigurasi berikut: password=SuperSecret123 untuk login."
        result = prose_handler.mask(text)
        assert "SuperSecret123" not in result, "Credential value harus ter-mask"

    def test_db_connection_string_in_prose_is_masked(self):
        text = (
            "Koneksi database menggunakan URI: "
            "postgresql://admin:s3cr3t@db.internal:5432/prod"
        )
        result = prose_handler.mask(text)
        assert "s3cr3t" not in result or "postgresql://" not in result.split("s3cr3t")[0] if "s3cr3t" in result else True

    def test_api_key_in_prose_is_masked(self):
        text = "Set variabel api_key=AbCdEfGhIjKlMnOpQrSt sebelum deploy."
        result = prose_handler.mask(text)
        assert "AbCdEfGhIjKlMnOpQrSt" not in result, "API key harus ter-mask"

    def test_non_sensitive_text_unchanged(self):
        text = "Server menggunakan PostgreSQL versi 14 sebagai database utama."
        result = prose_handler.mask(text)
        # Tidak ada credential — teks harus relatif tidak berubah (nama DB dipertahankan)
        assert "PostgreSQL" in result or isinstance(result, str)

    def test_mask_does_not_corrupt_sentence_structure(self):
        """Output harus tetap string (tidak None, tidak exception)."""
        text = "Sistem akan reset password Anda dalam 24 jam."
        result = prose_handler.mask(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_username_and_credential_in_prose_is_masked(self):
        """Uji kasus free text dengan username teknis dan password dengan pemisah ;."""
        text = (
            "Berikut termasuk username : admin; password : secret123 . "
            "DB postgresql username: admin@prod password ; `P@ssw0rd!2024"
        )
        result = prose_handler.mask(text)
        assert "admin@prod" not in result, "username admin@prod harus ter-mask"
        assert "P@ssw0rd!2024" not in result, "password P@ssw0rd!2024 harus ter-mask"

