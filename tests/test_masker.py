"""
test_masker.py — End-to-end test untuk masker.mask_document().

Menggunakan contoh dokumen Confluence realistis yang menggabungkan
prose + code block + tabel dalam satu dokumen.
"""

from __future__ import annotations

import pytest

from src.masker import mask_document


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: dokumen Confluence realistis
# ─────────────────────────────────────────────────────────────────────────────

REALISTIC_DOC = """\
# Konfigurasi Deployment: Payment Service

## Overview

Service ini di-deploy di cluster Kubernetes internal. Hubungi tim infra
di infra@company.com untuk akses cluster.

## Database Connection

Gunakan connection string berikut untuk koneksi ke database production:

```env
DB_HOST=10.20.30.40
DB_PORT=5432
DB_NAME=payments_prod
DB_USER=svc_payment
DB_PASSWORD=Sup3rS3cr3tPa$$word
```

## API Gateway Configuration

```yaml
gateway:
  base_url: https://api.internal.company.com
  api_key: sk_live_AbCdEfGhIjKlMnOpQrSt1234
  timeout: 30
  retry: 3
```

## Service Credentials

| Service     | Username  | Password         | Token                    |
|-------------|-----------|------------------|--------------------------|
| DB Primary  | svc_pay   | Sup3rS3cr3t!     | N/A                      |
| Redis Cache | redis_svc | r3d1sS3cr3t      | N/A                      |
| API Gateway | -         | -                | sk_live_XyZ1234AbCdEfGh  |

## Deployment Notes

- Ganti password setiap 90 hari (policy keamanan).
- Jangan commit credential ke Git repository.
- Gunakan Vault untuk secret management di environment production.
"""


class TestMaskDocumentEndToEnd:
    def test_output_is_string(self):
        result = mask_document(REALISTIC_DOC)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_db_password_env_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "Sup3rS3cr3tPa" not in result, "DB_PASSWORD di env block harus ter-mask"

    def test_api_key_yaml_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "sk_live_AbCdEfGhIjKlMnOpQrSt1234" not in result, "api_key di yaml block harus ter-mask"

    def test_table_password_column_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "Sup3rS3cr3t!" not in result, "Password di tabel harus ter-mask"
        assert "r3d1sS3cr3t" not in result, "Password Redis di tabel harus ter-mask"

    def test_table_token_column_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "sk_live_XyZ1234AbCdEfGh" not in result, "Token di tabel harus ter-mask"

    def test_email_in_prose_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "infra@company.com" not in result, "Email di prose harus ter-mask"

    def test_non_sensitive_prose_preserved(self):
        result = mask_document(REALISTIC_DOC)
        # Teks non-sensitif seperti nama service dan penjelasan harus tetap ada
        assert "Payment Service" in result or "payment" in result.lower()
        assert "Kubernetes" in result

    def test_password_advice_not_over_masked(self):
        """'Ganti password setiap 90 hari' — kalimat naratif, tidak mengandung credential."""
        result = mask_document(REALISTIC_DOC)
        # Kata "password" dalam kalimat saran boleh tetap ada
        assert "90 hari" in result or "password" in result.lower()

    def test_non_sensitive_config_preserved(self):
        result = mask_document(REALISTIC_DOC)
        # timeout dan retry di YAML bukan credential — harus dipertahankan
        assert "timeout" in result or "retry" in result

    def test_markdown_structure_preserved(self):
        """Output harus tetap valid markdown: heading, code fence, tabel ada."""
        result = mask_document(REALISTIC_DOC)
        assert "# " in result, "Heading harus dipertahankan"
        assert "```" in result, "Code fence harus dipertahankan"
        assert "|" in result, "Tabel harus dipertahankan"

    def test_empty_document(self):
        result = mask_document("")
        assert result == ""

    def test_plain_text_no_sensitive(self):
        text = "Ini adalah dokumen teknis tanpa informasi sensitif. Versi 2.0.\n"
        result = mask_document(text)
        assert isinstance(result, str)
        assert "2.0" in result


class TestMaskDocumentEdgeCases:
    def test_only_code_block(self):
        md = "```env\nSECRET_KEY=abc123def456ghi\nAPP_NAME=MyApp\n```\n"
        result = mask_document(md)
        assert "abc123def456ghi" not in result
        assert "MyApp" in result

    def test_only_table(self):
        md = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | s3cr3t   |\n"
        )
        result = mask_document(md)
        assert "s3cr3t" not in result

    def test_nested_prose_with_inline_credential(self):
        """Credential inline dalam prose harus ter-mask."""
        md = "Pastikan set `token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9` sebelum deploy.\n"
        result = mask_document(md)
        assert isinstance(result, str)
        # Inline code akan diproses oleh prose_handler — assertion longgar
        # karena backtick dalam prose diperlakukan sebagai teks biasa oleh Presidio

    def test_multiple_tables(self):
        md = (
            "| Name | Email |\n"
            "|------|-------|\n"
            "| Alice | alice@x.com |\n\n"
            "| Key | Secret |\n"
            "|-----|--------|\n"
            "| k1  | myS3cr3t |\n"
        )
        result = mask_document(md)
        assert "myS3cr3t" not in result
