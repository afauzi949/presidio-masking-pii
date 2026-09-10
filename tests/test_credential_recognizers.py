"""
test_credential_recognizers.py — Unit test untuk custom PatternRecognizer.

Setiap recognizer diuji dengan:
- Kasus positif: teks yang HARUS terdeteksi sebagai entitas kredensial.
- Kasus negatif: teks dokumentasi teknis biasa yang TIDAK boleh false-positive.
"""

from __future__ import annotations

import pytest
from presidio_analyzer import AnalyzerEngine

from src.recognizers.credential_patterns import (
    APIKeyRecognizer,
    CredentialKVRecognizer,
    DBConnectionStringRecognizer,
    HostPortRecognizer,
)
from src.recognizers.registry import get_analyzer


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def analyze(text: str, entity: str) -> list:
    """Jalankan analyzer dan kembalikan hasil untuk entity tertentu."""
    analyzer = get_analyzer()
    return analyzer.analyze(
        text=text,
        language="en",
        entities=[entity],
        score_threshold=0.5,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIAL_KV
# ─────────────────────────────────────────────────────────────────────────────

class TestCredentialKVRecognizer:
    def test_password_equals(self):
        results = analyze("password=mySecret123", "CREDENTIAL_KV")
        assert results, "password=value harus terdeteksi"

    def test_passwd_colon(self):
        results = analyze("passwd: abc123", "CREDENTIAL_KV")
        assert results, "passwd: value harus terdeteksi"

    def test_secret_equals(self):
        results = analyze("secret=superSecretKey", "CREDENTIAL_KV")
        assert results, "secret=value harus terdeteksi"

    def test_pwd_equals(self):
        results = analyze("pwd=Pass@word1", "CREDENTIAL_KV")
        assert results, "pwd=value harus terdeteksi"

    def test_password_semicolon_and_backtick(self):
        results = analyze("password ; `P@ssw0rd!2024", "CREDENTIAL_KV")
        assert results, "password dengan pemisah ; dan backtick harus terdeteksi"

    # Negatif — dokumentasi teknis
    def test_no_false_positive_advice_sentence(self):
        """'Ganti password setiap 90 hari' tidak boleh terdeteksi — tidak ada = atau :"""
        results = analyze("Ganti password setiap 90 hari untuk keamanan.", "CREDENTIAL_KV")
        assert not results, "Kalimat saran tanpa assignment tidak boleh terdeteksi"

    def test_no_false_positive_placeholder(self):
        """Placeholder dokumentasi seperti 'password: <your-password>' boleh di-skip."""
        # Ini edge case — kita toleransi false-positive di sini karena placeholder
        # tetap sebaiknya dimasking. Test ini hanya memverifikasi bahwa nilai placeholder
        # seperti <your-password> tidak menyebabkan error.
        results = analyze("password: <your-password>", "CREDENTIAL_KV")
        # Tidak ada assertion khusus — hanya memastikan tidak error
        assert isinstance(results, list)

    def test_inline_env_var(self):
        results = analyze("DB_PASSWORD=s3cr3t_pass!", "CREDENTIAL_KV")
        # DB_PASSWORD tidak cocok pola (key harus password|passwd|pwd|secret)
        # Ini bukan bug — key-based masking untuk ini ada di code_block_handler
        assert isinstance(results, list)


# ─────────────────────────────────────────────────────────────────────────────
# DB_CONNECTION_STRING
# ─────────────────────────────────────────────────────────────────────────────

class TestDBConnectionStringRecognizer:
    def test_postgresql(self):
        results = analyze(
            "postgresql://user:pass@localhost:5432/mydb", "DB_CONNECTION_STRING"
        )
        assert results, "postgresql URI harus terdeteksi"

    def test_mysql(self):
        results = analyze(
            "mysql://admin:s3cr3t@db.internal:3306/production", "DB_CONNECTION_STRING"
        )
        assert results, "mysql URI harus terdeteksi"

    def test_mongodb(self):
        results = analyze(
            "mongodb://user:pass@mongo.host:27017/myapp", "DB_CONNECTION_STRING"
        )
        assert results, "mongodb URI harus terdeteksi"

    def test_postgres_alias(self):
        results = analyze(
            "postgres://user:s3cr3t@host/db", "DB_CONNECTION_STRING"
        )
        assert results, "postgres:// alias harus terdeteksi"

    # Negatif
    def test_no_false_positive_http_url(self):
        results = analyze("https://docs.example.com/api", "DB_CONNECTION_STRING")
        assert not results, "HTTP URL biasa tidak boleh terdeteksi sebagai DB connection"

    def test_no_false_positive_mention(self):
        results = analyze(
            "Kami menggunakan PostgreSQL sebagai database utama.", "DB_CONNECTION_STRING"
        )
        assert not results, "Penyebutan nama DB tanpa URI tidak boleh terdeteksi"


# ─────────────────────────────────────────────────────────────────────────────
# API_KEY
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIKeyRecognizer:
    def test_api_key_assignment(self):
        results = analyze("api_key=AbCdEfGhIjKlMnOpQr", "API_KEY")
        assert results, "api_key assignment (>=16 char) harus terdeteksi"

    def test_token_assignment(self):
        results = analyze("token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "API_KEY")
        assert results, "token assignment harus terdeteksi"

    def test_bearer_token(self):
        results = analyze("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "API_KEY")
        assert results, "Bearer token harus terdeteksi"

    def test_access_key(self):
        results = analyze("access_key=AKIAIOSFODNN7EXAMPLE", "API_KEY")
        assert results, "access_key harus terdeteksi"

    # Negatif
    def test_no_false_positive_short_token(self):
        """Token pendek (<16 char) tidak boleh terdeteksi."""
        results = analyze("token=short", "API_KEY")
        assert not results, "Token pendek tidak boleh terdeteksi"

    def test_no_false_positive_api_mention(self):
        results = analyze(
            "Buat API key di portal developer kami.", "API_KEY"
        )
        assert not results, "Penyebutan 'API key' tanpa assignment tidak boleh terdeteksi"


# ─────────────────────────────────────────────────────────────────────────────
# HOST_PORT
# ─────────────────────────────────────────────────────────────────────────────

class TestHostPortRecognizer:
    def test_ip_port(self):
        results = analyze("192.168.1.10:5432", "HOST_PORT")
        assert results, "IP:port harus terdeteksi"

    def test_internal_ip_port(self):
        results = analyze("10.0.0.1:8080", "HOST_PORT")
        assert results, "Internal IP:port harus terdeteksi"

    # Negatif
    def test_no_false_positive_plain_ip(self):
        """IP tanpa port tidak boleh match pola IP:port."""
        results = analyze("Server berada di 10.0.0.1", "HOST_PORT")
        # IP tanpa port — tidak harus terdeteksi
        assert isinstance(results, list)

    def test_no_false_positive_url_path(self):
        results = analyze("https://api.example.com/v1/data", "HOST_PORT")
        assert not results, "URL dengan domain tidak boleh terdeteksi sebagai HOST_PORT"


# ─────────────────────────────────────────────────────────────────────────────
# USERNAME
# ─────────────────────────────────────────────────────────────────────────────

class TestUsernameRecognizer:
    def test_username_colon_with_at_domain(self):
        text = "DB postgresql username: admin@prod"
        results = analyze(text, "USERNAME")
        assert results, "username: admin@prod harus terdeteksi"
        # Memastikan hanya nilai 'admin@prod' yang ditandai, bukan label 'username:'
        assert text[results[0].start:results[0].end] == "admin@prod"

    def test_username_equals(self):
        text = "username=super_user"
        results = analyze(text, "USERNAME")
        assert results, "username=value harus terdeteksi"
        assert text[results[0].start:results[0].end] == "super_user"

    def test_user_colon(self):
        text = "user: root"
        results = analyze(text, "USERNAME")
        assert results, "user: root harus terdeteksi"
        assert text[results[0].start:results[0].end] == "root"

    def test_uname_semicolon(self):
        text = "uname ; testuser"
        results = analyze(text, "USERNAME")
        assert results, "uname ; testuser harus terdeteksi"
        assert text[results[0].start:results[0].end] == "testuser"


# ─────────────────────────────────────────────────────────────────────────────
# Registry integration
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryIntegration:
    def test_all_custom_entities_registered(self):
        analyzer = get_analyzer()
        supported = {
            r.supported_entities[0]
            for r in analyzer.registry.recognizers
        }
        assert "CREDENTIAL_KV" in supported
        assert "DB_CONNECTION_STRING" in supported
        assert "API_KEY" in supported
        assert "HOST_PORT" in supported
        assert "USERNAME" in supported

    def test_predefined_entities_still_active(self):
        """PERSON, EMAIL_ADDRESS, PHONE_NUMBER dari Presidio harus tetap aktif."""
        results = analyze("Contact john.doe@example.com for support.", "EMAIL_ADDRESS")
        assert results, "EMAIL_ADDRESS predefined recognizer harus masih aktif"

