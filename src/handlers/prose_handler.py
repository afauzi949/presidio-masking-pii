"""
prose_handler.py — Handler untuk segmen prose (teks naratif).

Menjalankan pipeline Presidio penuh:
  1. AnalyzerEngine.analyze() — deteksi entitas (predefined + custom recognizer).
  2. AnonymizerEngine.anonymize() — terapkan operator masking per entitas.

Operator masking ditentukan dari config:
  - MASK_REDACT_ENTITIES  → Replace operator (full mask dengan placeholder)
  - MASK_PARTIAL_ENTITIES → Mask operator (partial, karakter pertama/terakhir dipertahankan)
"""

from __future__ import annotations

from typing import Dict

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from src.config.settings import settings
from src.recognizers.registry import get_analyzer


# ─────────────────────────────────────────────────────────────────────────────
# Anonymizer operator builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_operators() -> Dict[str, OperatorConfig]:
    """
    Bangun dict operator Presidio dari konfigurasi settings.

    Redact   → Replace dengan "<ENTITY_TYPE>"
    Partial  → Mask tengah, pertahankan 1 karakter awal dan akhir
    """
    operators: Dict[str, OperatorConfig] = {}

    for entity in settings.redact_entities_set:
        operators[entity] = OperatorConfig(
            operator_name="replace",
            params={"new_value": f"<{entity}>"},
        )

    for entity in settings.partial_entities_set:
        operators[entity] = OperatorConfig(
            operator_name="mask",
            params={
                "masking_char": "*",
                "chars_to_mask": 100,   # besar; di-trim oleh Presidio ke panjang aktual
                "from_end": False,
            },
        )

    return operators


# Lazy singleton: operator dict dibangun sekali saat module pertama diakses
_operators: Dict[str, OperatorConfig] | None = None
_anonymizer: AnonymizerEngine | None = None


def _get_anonymizer() -> AnonymizerEngine:
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def _get_operators() -> Dict[str, OperatorConfig]:
    global _operators
    if _operators is None:
        _operators = _build_operators()
    return _operators


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def mask(text: str, analyzer: AnalyzerEngine | None = None) -> str:
    """
    Jalankan Presidio analyze + anonymize pada *text* prose.

    Args:
        text:     Teks prose mentah (paragraf, heading, list item, dst.)
        analyzer: AnalyzerEngine yang digunakan. Jika None, gunakan instance
                  global dari registry (yang sudah include custom recognizer).

    Returns:
        Teks setelah masking. Entitas yang terdeteksi di-replace sesuai
        operator yang dikonfigurasi di .env.
    """
    if not text or not text.strip():
        return text

    if analyzer is None:
        analyzer = get_analyzer()

    anonymizer = _get_anonymizer()
    operators = _get_operators()

    results = analyzer.analyze(
        text=text,
        language=settings.presidio_language,
        entities=settings.entities_list,
        score_threshold=settings.presidio_score_threshold,
    )

    if not results:
        return text

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    return anonymized.text
