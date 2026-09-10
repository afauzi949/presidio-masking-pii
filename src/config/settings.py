"""
settings.py — Konfigurasi service, hardcoded langsung di kode (bukan dari .env).

Semua nilai yang diakses dari kode lain harus melalui objek `settings` di sini,
bukan ditulis ulang di tiap file, supaya tetap satu sumber kebenaran.

Catatan:
- PERSON sengaja TIDAK dimasukkan ke `presidio_entities` — service ini tidak
  memanfaatkan predefined recognizer NER Presidio untuk nama orang.
- `spacy_model_name` dipakai oleh `src.recognizers.registry` untuk membangun
  NlpEngineProvider secara eksplisit (model kecil, karena NER PERSON tidak dipakai).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Settings:
    # --- Presidio core ---
    presidio_language: str = "en"
    presidio_score_threshold: float = 0.6
    spacy_model_name: str = "en_core_web_sm"

    presidio_entities: tuple = (
        "EMAIL_ADDRESS", "PHONE_NUMBER",
        "CREDENTIAL_KV", "DB_CONNECTION_STRING", "API_KEY", "HOST_PORT", "USERNAME",
    )

    # --- Masking strategies ---
    mask_redact_entities: tuple = ("CREDENTIAL_KV", "DB_CONNECTION_STRING", "API_KEY")
    mask_partial_entities: tuple = ("EMAIL_ADDRESS", "PHONE_NUMBER", "HOST_PORT", "USERNAME")

    # --- Key hints (code block / table key-based matching) ---
    credential_key_hints: tuple = (
        "password", "passwd", "pwd", "secret", "token", "api_key",
        "db_pass", "username", "user", "host", "port",
    )

    # --- Table sensitive columns ---
    table_sensitive_columns: tuple = (
        "password", "secret", "token", "api_key", "credential", "username",
    )

    # ------------------------------------------------------------------ #
    # Computed helpers (parsed lists)                                      #
    # ------------------------------------------------------------------ #

    @property
    def entities_list(self) -> List[str]:
        return list(self.presidio_entities)

    @property
    def redact_entities_set(self) -> set:
        return set(self.mask_redact_entities)

    @property
    def partial_entities_set(self) -> set:
        return set(self.mask_partial_entities)

    @property
    def credential_key_hints_list(self) -> List[str]:
        return [k.lower() for k in self.credential_key_hints]

    @property
    def table_sensitive_columns_list(self) -> List[str]:
        return [c.lower() for c in self.table_sensitive_columns]


# Convenience singleton — gunakan ini di seluruh codebase
settings = Settings()
