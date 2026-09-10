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
- USERNAME              : nilai username pada pola key-value

PENTING — span hasil deteksi (`start`/`end`) untuk CREDENTIAL_KV, API_KEY, dan
USERNAME HANYA mencakup nilainya (value), bukan label ("password:") atau tanda
kutip/backtick di sekitarnya. Ini wajib untuk skema replace-balik literal value
ke markdown asli di `src/replace_engine.py` — kalau span ikut menyertakan label,
literal hasil capture ("Password: mySecret") tidak akan pernah cocok dengan raw
markdown yang isinya cuma "mySecret" (mis. di dalam sel tabel). Recognizer yang
butuh perilaku ini meng-override `analyze()` dan mengembalikan span dari capture
group value saja — pola yang sama seperti `UsernameRecognizer` di bawah.
DB_CONNECTION_STRING dan HOST_PORT tidak butuh override karena pattern-nya
memang cuma cocok ke value itu sendiri (tidak ada label di depan match).
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

    REGEX_STR = (
        r"(?i)\b(?:[a-z_]*password|passwd|pwd|secret|passphrase|db_pass)\b"
        r"\s*[:=;]\s*[`\"']?([^\s`\"',;]+)"
    )
    COMPILED_REGEX = re.compile(REGEX_STR)

    CONTEXT = ["password", "credential", "secret", "login", "auth", "passwd", "pwd"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="CREDENTIAL_KV",
            name="CredentialKVRecognizer",
            patterns=[Pattern(name="credential_kv", regex=self.REGEX_STR, score=0.75)],
            context=self.CONTEXT,
            supported_language="en",
        )

    def analyze(self, text: str, entities: list[str] | None = None, nlp_artifacts=None) -> list[RecognizerResult]:
        results: list[RecognizerResult] = []
        if entities and "CREDENTIAL_KV" not in entities:
            return results

        for match in self.COMPILED_REGEX.finditer(text):
            val_text = match.group(1)
            if not val_text:
                continue

            explanation = AnalysisExplanation(
                recognizer=self.name,
                original_score=0.75,
                pattern_name="credential_kv",
                pattern=self.REGEX_STR,
            )
            results.append(
                RecognizerResult(
                    entity_type="CREDENTIAL_KV",
                    start=match.start(1),
                    end=match.end(1),
                    score=0.75,
                    analysis_explanation=explanation,
                )
            )
        return results


# ─────────────────────────────────────────────────────────────────────────────
# DB_CONNECTION_STRING
# Menangkap: postgresql://user:pass@host:5432/db
# ─────────────────────────────────────────────────────────────────────────────

class DBConnectionStringRecognizer(PatternRecognizer):
    """
    PatternRecognizer untuk URI koneksi database.

    Char class di akhir pattern sengaja mengecualikan backtick/kutip/kurung
    supaya URI yang ditulis dalam inline code (`` `postgresql://...` ``) tidak
    ikut menyeret karakter markup di sekitarnya ke dalam span.
    """

    PATTERNS = [
        Pattern(
            name="db_connection_string",
            regex=(
                r"(?i)"
                r"(?:postgresql|postgres|mysql|mongodb|mongo|redis|mssql|oracle|sqlite)"
                r"(?:\+\w+)?://[^\s`\"'<>)]+:[^\s`\"'<>)]+@[^\s`\"'<>)]+"
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
# Menangkap: api_key=AbCdEfGhIjKlMnOpQr, token: Bearer eyJhb..., API_KEY=...
# Minimum 16 karakter supaya false-positive rendah
# ─────────────────────────────────────────────────────────────────────────────

class APIKeyRecognizer(PatternRecognizer):
    """
    PatternRecognizer untuk API key dan token assignment.

    Sama seperti CredentialKVRecognizer, `analyze()` di-override supaya span
    hasil deteksi cuma value-nya (bukan label "api_key=" atau kata "Bearer").
    """

    ASSIGNMENT_REGEX_STR = (
        r"(?i)\b(?:api[_\-]?key|access[_\-]?key|token|secret[_\-]?key|auth[_\-]?token)\b"
        r"\s*[:=]\s*[`\"']?([A-Za-z0-9\-_.~+/]{16,})"
    )
    BEARER_REGEX_STR = r"(?i)\bBearer\s+([A-Za-z0-9\-_.~+/=]{20,})"

    COMPILED_ASSIGNMENT = re.compile(ASSIGNMENT_REGEX_STR)
    COMPILED_BEARER = re.compile(BEARER_REGEX_STR)

    CONTEXT = ["api", "key", "token", "auth", "authorization", "access", "secret"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="API_KEY",
            name="APIKeyRecognizer",
            patterns=[
                Pattern(name="api_key_assignment", regex=self.ASSIGNMENT_REGEX_STR, score=0.80),
                Pattern(name="bearer_token", regex=self.BEARER_REGEX_STR, score=0.85),
            ],
            context=self.CONTEXT,
            supported_language="en",
        )

    def analyze(self, text: str, entities: list[str] | None = None, nlp_artifacts=None) -> list[RecognizerResult]:
        results: list[RecognizerResult] = []
        if entities and "API_KEY" not in entities:
            return results

        for match in self.COMPILED_ASSIGNMENT.finditer(text):
            results.append(self._result(match, "api_key_assignment", 0.80))
        for match in self.COMPILED_BEARER.finditer(text):
            results.append(self._result(match, "bearer_token", 0.85))
        return results

    def _result(self, match: re.Match, pattern_name: str, score: float) -> RecognizerResult:
        explanation = AnalysisExplanation(
            recognizer=self.name,
            original_score=score,
            pattern_name=pattern_name,
            pattern=match.re.pattern,
        )
        return RecognizerResult(
            entity_type="API_KEY",
            start=match.start(1),
            end=match.end(1),
            score=score,
            analysis_explanation=explanation,
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
