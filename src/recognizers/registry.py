"""
registry.py — Bangun dan kembalikan AnalyzerEngine Presidio yang sudah
didaftarkan custom credential recognizer.

Satu `AnalyzerEngine` bersama dipakai oleh semua handler — predefined recognizer
(EMAIL_ADDRESS, PHONE_NUMBER, dst.) tetap aktif berbarengan dengan custom
recognizer kredensial. PERSON tidak dipakai (lihat `src.config.settings`), jadi
NlpEngine dibangun eksplisit dengan model spaCy kecil (`en_core_web_sm`) alih-alih
model besar bawaan default Presidio — cukup untuk tokenization/lemma yang
dipakai context-enhancement, tanpa beban NER model besar yang tidak dimanfaatkan.

Gunakan `get_analyzer()` untuk mendapatkan instance yang di-cache (dibuat sekali
saat startup, bukan per-request).
"""

from __future__ import annotations

from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from src.config.settings import settings
from src.recognizers.credential_patterns import get_all_credential_recognizers


def _build_nlp_engine():
    """Bangun NlpEngine dengan model spaCy kecil yang dikonfigurasi di settings."""
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": settings.presidio_language, "model_name": settings.spacy_model_name}
        ],
    }
    return NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()


@lru_cache(maxsize=1)
def get_analyzer() -> AnalyzerEngine:
    """
    Bangun AnalyzerEngine (model spaCy kecil) dengan semua custom recognizer terdaftar.

    Cache dengan lru_cache(1) supaya spaCy model tidak di-load ulang
    setiap request.
    """
    analyzer = AnalyzerEngine(nlp_engine=_build_nlp_engine())

    for recognizer in get_all_credential_recognizers():
        analyzer.registry.add_recognizer(recognizer)

    return analyzer
