"""
test_masker.py — End-to-end test untuk masker.mask_document().

Menggunakan dokumen "Konfigurasi Server Produksi" yang menggabungkan prose,
list (VPN multi-baris), code block (.env / yaml / json), tabel, connection
string, dan Bearer token dalam satu dokumen — sesuai regression test utama
yang diminta di plan.md.

Skema: segmentasi → restrukturisasi → Presidio Analyzer sekali untuk seluruh
dokumen → replace literal value ke markdown ASLI (bukan ke teks rekonstruksi).
"""

from __future__ import annotations

from src.masker import mask_document

# ─────────────────────────────────────────────────────────────────────────────
# Fixture: dokumen "Konfigurasi Server Produksi"
# ─────────────────────────────────────────────────────────────────────────────

REALISTIC_DOC = """\
# Konfigurasi Server Produksi

## Overview

Server ini melayani traffic production. Hubungi tim infra di
infra@company.com untuk akses lebih lanjut.

## Database Connection

Gunakan connection string berikut untuk koneksi ke database production:

```env
DB_HOST=10.20.30.40
DB_PORT=5432
DB_NAME=payments_prod
DB_USER=svc_payment
DB_PASSWORD=Sup3rS3cr3tPa55word
```

Atau langsung lewat URI: postgresql://svc_payment:Sup3rS3cr3tPa55word@10.20.30.40:5432/payments_prod

## API Gateway Configuration

```yaml
gateway:
  base_url: https://api.internal.company.com
  api_key: sk_live_AbCdEfGhIjKlMnOpQrSt1234
  timeout: 30
  retry: 3
```

## App Config (JSON)

```json
{
  "app_name": "PaymentService",
  "version": "1.0",
  "password": "JsonBlockSecret99"
}
```

## Service Credentials

| Service     | Username  | Password         | Token                    |
|-------------|-----------|------------------|--------------------------|
| DB Primary  | svc_pay   | Sup3rS3cr3t!     | N/A                      |
| Redis Cache | redis_svc | r3d1sS3cr3t      | N/A                      |
| API Gateway | -         | -                | sk_live_XyZ1234AbCdEfGh  |

## VPN Access

- Username:
  vpnuser
- Password:
  Vpn@ccess2024!

## curl Example

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef" https://api.internal.company.com
```

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

    def test_email_in_prose_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "infra@company.com" not in result

    def test_db_password_env_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "Sup3rS3cr3tPa55word" not in result

    def test_db_connection_string_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "postgresql://svc_payment:Sup3rS3cr3tPa55word@10.20.30.40:5432/payments_prod" not in result

    def test_api_key_yaml_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "sk_live_AbCdEfGhIjKlMnOpQrSt1234" not in result

    def test_json_block_password_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "JsonBlockSecret99" not in result

    def test_json_block_non_sensitive_preserved(self):
        result = mask_document(REALISTIC_DOC)
        assert "PaymentService" in result

    def test_table_password_column_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "Sup3rS3cr3t!" not in result
        assert "r3d1sS3cr3t" not in result

    def test_table_token_column_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "sk_live_XyZ1234AbCdEfGh" not in result

    def test_table_username_column_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "svc_pay" not in result
        assert "redis_svc" not in result

    def test_table_header_preserved(self):
        result = mask_document(REALISTIC_DOC)
        assert "Service" in result and "Password" in result

    def test_vpn_multiline_username_and_password_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "vpnuser" not in result
        assert "Vpn@ccess2024!" not in result

    def test_bearer_token_masked(self):
        result = mask_document(REALISTIC_DOC)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef" not in result

    def test_non_sensitive_prose_preserved(self):
        result = mask_document(REALISTIC_DOC)
        assert "Konfigurasi Server Produksi" in result
        assert "production" in result.lower()

    def test_password_advice_not_over_masked(self):
        """'Ganti password setiap 90 hari' — kalimat naratif, tidak mengandung credential."""
        result = mask_document(REALISTIC_DOC)
        assert "90 hari" in result

    def test_non_sensitive_config_preserved(self):
        result = mask_document(REALISTIC_DOC)
        assert "timeout" in result
        assert "retry" in result

    def test_markdown_structure_preserved(self):
        """Output harus tetap valid markdown: heading, code fence, tabel ada."""
        result = mask_document(REALISTIC_DOC)
        assert "# " in result
        assert "```" in result
        assert "|" in result

    def test_placeholder_used(self):
        result = mask_document(REALISTIC_DOC)
        assert "<REDACTED>" in result

    def test_empty_document(self):
        assert mask_document("") == ""

    def test_plain_text_no_sensitive(self):
        text = "Ini adalah dokumen teknis tanpa informasi sensitif. Versi 2.0.\n"
        result = mask_document(text)
        assert "2.0" in result


class TestMaskDocumentEdgeCases:
    def test_only_code_block(self):
        md = "```env\nSECRET_KEY=abc123def456ghi789\nAPP_NAME=MyApp\n```\n"
        result = mask_document(md)
        assert "abc123def456ghi789" not in result
        assert "MyApp" in result

    def test_only_table(self):
        md = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB      | s3cr3tval |\n"
        )
        result = mask_document(md)
        assert "s3cr3tval" not in result

    def test_nested_prose_with_inline_credential(self):
        """Credential inline dalam prose harus ter-mask."""
        md = "Pastikan set `token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9` sebelum deploy.\n"
        result = mask_document(md)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_multiple_tables(self):
        md = (
            "| Name | Email |\n"
            "|------|-------|\n"
            "| Alice | alice@x.com |\n\n"
            "| Key | Secret |\n"
            "|-----|--------|\n"
            "| k1  | myS3cr3tValue |\n"
        )
        result = mask_document(md)
        assert "myS3cr3tValue" not in result

    def test_document_without_any_sensitive_data(self):
        md = "# Notes\n\nJust a regular document about the weather.\n"
        result = mask_document(md)
        assert "Just a regular document about the weather." in result
        assert "<REDACTED>" not in result
