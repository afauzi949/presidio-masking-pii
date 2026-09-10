"""
masker.py — Orchestrator skema "restrukturisasi + Presidio + replace-balik".

Flow (lihat plan.md untuk rasional lengkap):
    1. Segmentasi markdown asli jadi list Segment (prose/code_block/table).
    2. Tiap segmen direstrukturisasi jadi teks polos yang bisa dianalisis:
       - table      → table_to_sentence   (baris "Header: value" per field)
       - code_block → code_block_to_lines (fence dibuang, KV multi-baris digabung)
       - prose      → strip_markdown      (markup dibuang, isi teks dipertahankan)
    3. Semua hasil digabung jadi SATU teks rekonstruksi, dianalisis Presidio
       SEKALI untuk seluruh dokumen (bukan per segmen) — supaya deteksi kredensial
       tetap satu sumber kebenaran (regex + NER + custom recognizer + context).
    4. Literal value dari hasil deteksi dikumpulkan (dedup, urut DESC by length),
       lalu di-replace langsung ke markdown ASLI — bukan ke teks rekonstruksi —
       supaya format tabel/list/heading/code fence di output tetap utuh.
"""

from __future__ import annotations

from src.config.settings import settings
from src.recognizers.registry import get_analyzer
from src.reconstruction.code_block_to_lines import code_block_to_lines
from src.reconstruction.strip_markdown import strip_markdown
from src.reconstruction.table_to_sentence import table_to_sentence
from src.replace_engine import DEFAULT_PLACEHOLDER, collect_literal_values, replace_into_original
from src.segmentation import markdown_parser


def _reconstruct(raw_markdown: str) -> str:
    """Segmentasi + restrukturisasi seluruh dokumen jadi satu teks polos."""
    segments = markdown_parser.parse(raw_markdown)

    parts: list[str] = []
    for seg in segments:
        if seg.type == "table":
            parts.append(table_to_sentence(seg.content))
        elif seg.type == "code_block":
            parts.append(code_block_to_lines(seg.content, seg.meta.get("lang")))
        else:  # "prose" (dan "inline_code" kalau ada — diperlakukan sebagai teks biasa)
            parts.append(strip_markdown(seg.content))

    return "\n".join(p for p in parts if p)


def mask_document(raw_markdown: str) -> str:
    """
    Mask seluruh dokumen markdown: deteksi kredensial + PII, lalu ganti tiap
    value yang terdeteksi dengan placeholder di markdown ASLI.

    Args:
        raw_markdown: Teks markdown mentah.

    Returns:
        Markdown asli dengan value sensitif ter-mask; struktur (heading, code
        fence, tabel, list) tetap utuh karena masking terjadi lewat replace ke
        dokumen asli, bukan lewat penggabungan ulang segmen yang sudah di-mask.
    """
    if not raw_markdown:
        return raw_markdown

    reconstructed_text = _reconstruct(raw_markdown)
    if not reconstructed_text.strip():
        return raw_markdown

    analyzer = get_analyzer()
    results = analyzer.analyze(
        text=reconstructed_text,
        language=settings.presidio_language,
        entities=settings.entities_list,
        score_threshold=settings.presidio_score_threshold,
    )

    if not results:
        return raw_markdown

    values = collect_literal_values(reconstructed_text, results)
    if not values:
        return raw_markdown

    return replace_into_original(raw_markdown, values, placeholder=DEFAULT_PLACEHOLDER)


def mask_text(text: str) -> str:
    """Alias untuk mask_document."""
    return mask_document(text)
