"""
settings.py — Konfigurasi service, hardcoded langsung di kode (bukan dari .env).

Semua nilai yang diakses dari kode lain harus melalui objek `settings` di sini,
bukan ditulis ulang di tiap file, supaya tetap satu sumber kebenaran.

Catatan:
- PERSON sengaja TIDAK dimasukkan ke `presidio_entities` — service ini tidak
  memanfaatkan predefined recognizer NER Presidio untuk nama orang.
- `spacy_model_name` dipakai oleh `src.recognizers.registry` untuk membangun
  NlpEngineProvider secara eksplisit (model kecil, karena NER PERSON tidak dipakai).
- Tidak ada lagi konfigurasi redact/partial per entity atau whitelist nama
  kolom/key (`MASK_REDACT_ENTITIES`, `TABLE_SENSITIVE_COLUMNS`, dst.) — sejak
  migrasi ke skema restrukturisasi + replace-balik (lihat plan.md), semua entity
  yang terdeteksi Presidio diganti placeholder seragam lewat `src.replace_engine`,
  dan deteksi kredensial tidak lagi bergantung whitelist kolom/key manual.
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

    # ------------------------------------------------------------------ #
    # Computed helpers (parsed lists)                                      #
    # ------------------------------------------------------------------ #

    @property
    def entities_list(self) -> List[str]:
        return list(self.presidio_entities)


# Convenience singleton — gunakan ini di seluruh codebase
settings = Settings()
