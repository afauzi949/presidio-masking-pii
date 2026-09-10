"""
masker.py — Orchestrator: memproses teks bebas secara langsung via prose_handler.
"""

from __future__ import annotations

from src.handlers import prose_handler


def mask_document(text: str) -> str:
    """
    Mask seluruh dokumen teks bebas (free-text).
    Teks diproses langsung oleh Presidio Analyzer + Anonymizer
    tanpa melalui markdown parser.

    Args:
        text: Teks bebas / naratif mentah.

    Returns:
        Teks dengan semua entitas sensitif ter-mask.
    """
    if not text:
        return text

    return prose_handler.mask(text)


def mask_text(text: str) -> str:
    """Alias untuk mask_document."""
    return mask_document(text)

