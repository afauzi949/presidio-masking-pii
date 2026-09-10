"""
credential_patterns.py — Custom PatternRecognizer untuk entitas kredensial teknis.

Semua recognizer menggunakan `PatternRecognizer` dari Presidio, dilengkapi
dengan `context` words supaya confidence score lebih akurat dan false-positive
lebih rendah.

Entity types yang didefinisikan di sini:
- CREDENTIAL_KV         : key=value / key: value pattern (password, secret, dst.)
- DB_CONNECTION_STRING  : URI koneksi database (postgresql://, mysql://, dst.)
- API_KEY               : API key / token assignment
- HOST_PORT             : IP:port pattern
"""

import re
from presidio_analyzer import (
    AnalysisExplanation,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIAL_KV
# Menangkap: password=myS3cr3t, passwd: abc123, secret=xYz!, password ; `P@ssw0rd!2024
# Tidak cocok untuk: "ganti password setiap 90 hari" (tidak ada = atau :)
# ─────────────────────────────────────────────────────────────────────────────

class CredentialKVRecognizer(PatternRecognizer):
    """
    PatternRecognizer untuk password/secret key-value assignment.

    Pola: (password|passwd|pwd|secret|passphrase|db_pass) diikuti =, :, atau ; lalu nilai.
    Context words meningkatkan score saat kata di sekitarnya juga terkait credential.
    """

    PATTERNS = [
        Pattern(
            name="credential_kv",
            regex=(
                r"(?i)"
                r"(?:\b[a-z_]*password|\bpasswd|\bpwd|\bsecret|\bpassphrase|\bdb_pass)\b\s*[:=;]\s*[`\"']?\S+"
            ),
            score=0.75,
        ),
    ]

    CONTEXT = ["password", "credential", "secret", "login", "auth", "passwd", "pwd"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="CREDENTIAL_KV",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )


# ─────────────────────────────────────────────────────────────────────────────
# DB_CONNECTION_STRING
# Menangkap: postgresql://user:pass@host:5432/db
# ─────────────────────────────────────────────────────────────────────────────

class DBConnectionStringRecognizer(PatternRecognizer):
    """PatternRecognizer untuk URI koneksi database."""

    PATTERNS = [
        Pattern(
            name="db_connection_string",
            regex=(
                r"(?i)"
                r"(?:postgresql|postgres|mysql|mongodb|mongo|redis|mssql|oracle|sqlite)"
                r"(?:\+\w+)?://\S+:\S+@\S+"
            ),
            score=0.85,
        ),
    ]

    CONTEXT = ["database", "connection", "db", "server", "connect", "dsn", "url"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="DB_CONNECTION_STRING",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )


# ─────────────────────────────────────────────────────────────────────────────
# API_KEY
# Menangkap: api_key=AbCdEf1234567890, token: Bearer eyJhb..., API_KEY=...
# Minimum 16 karakter supaya false-positive rendah
# ─────────────────────────────────────────────────────────────────────────────

class APIKeyRecognizer(PatternRecognizer):
    """PatternRecognizer untuk API key dan token assignment."""

    PATTERNS = [
        Pattern(
            name="api_key_assignment",
            regex=(
                r"(?i)"
                r"(?:api[_\-]?key|access[_\-]?key|token|secret[_\-]?key|auth[_\-]?token)"
                r"\s*[:=]\s*[A-Za-z0-9\-_.~+/]{16,}"
            ),
            score=0.80,
        ),
        # Bearer token di header atau config
        Pattern(
            name="bearer_token",
            regex=r"(?i)Bearer\s+[A-Za-z0-9\-_.~+/=]{20,}",
            score=0.85,
        ),
    ]

    CONTEXT = ["api", "key", "token", "auth", "authorization", "access", "secret"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="API_KEY",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )


# ─────────────────────────────────────────────────────────────────────────────
# HOST_PORT
# Menangkap: 192.168.1.10:5432, 10.0.0.1:8080
# ─────────────────────────────────────────────────────────────────────────────

class HostPortRecognizer(PatternRecognizer):
    """PatternRecognizer untuk IP:port pattern."""

    PATTERNS = [
        Pattern(
            name="ip_port",
            regex=(
                r"\b"
                r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
                r":\d{2,5}"
                r"\b"
            ),
            score=0.70,
        ),
    ]

    CONTEXT = ["server", "host", "endpoint", "address", "ip", "port", "connect"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="HOST_PORT",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )


# ─────────────────────────────────────────────────────────────────────────────
# USERNAME
# Menangkap nilai username pada pola: username: admin@prod, user=john, uname: test
# ─────────────────────────────────────────────────────────────────────────────

class UsernameRecognizer(PatternRecognizer):
    """
    PatternRecognizer untuk mendeteksi nilai username/user identifier dalam pola key-value.

    Pola: (username|user_name|uname|user id|userid|db_user|user) diikuti : atau = atau ;
    lalu nilai username.
    Hanya menargetkan nilai username (bukan label 'username:') agar label tetap terbaca.
    """

    REGEX_STR = (
        r"(?i)\b(?:[a-z_]*username|user_name|uname|user\s*id|userid|db_user|user)\b"
        r"\s*[:=;]\s*"
        r"[`\"']?([^\s`\"',;]+)[`\"']?"
    )
    COMPILED_REGEX = re.compile(REGEX_STR)

    CONTEXT = ["username", "user", "login", "account", "auth", "credential", "admin", "db", "database"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="USERNAME",
            name="UsernameRecognizer",
            patterns=[
                Pattern(
                    name="username_kv",
                    regex=self.REGEX_STR,
                    score=0.85,
                )
            ],
            context=self.CONTEXT,
            supported_language="en",
        )

    def analyze(self, text: str, entities: list[str] | None = None, nlp_artifacts=None) -> list[RecognizerResult]:
        results: list[RecognizerResult] = []
        if entities and "USERNAME" not in entities:
            return results

        for match in self.COMPILED_REGEX.finditer(text):
            val_start = match.start(1)
            val_end = match.end(1)
            val_text = match.group(1)

            # Lewatkan jika nilainya kosong atau keyword umum yang bukan username
            if not val_text or val_text.lower() in ("null", "none", "true", "false"):
                continue

            explanation = AnalysisExplanation(
                recognizer=self.name,
                original_score=0.85,
                pattern_name="username_kv",
                pattern=self.REGEX_STR,
            )

            results.append(
                RecognizerResult(
                    entity_type="USERNAME",
                    start=val_start,
                    end=val_end,
                    score=0.85,
                    analysis_explanation=explanation,
                )
            )

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Factory: kembalikan semua recognizer sebagai list
# ─────────────────────────────────────────────────────────────────────────────

def get_all_credential_recognizers() -> list:
    """Kembalikan list instance semua custom credential recognizer."""
    return [
        CredentialKVRecognizer(),
        DBConnectionStringRecognizer(),
        APIKeyRecognizer(),
        HostPortRecognizer(),
        UsernameRecognizer(),
    ]

