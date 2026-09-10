"""
markdown_parser.py — Parse dokumen markdown menjadi list[Segment].

Segmentasi menggunakan markdown-it-py (token-based, bukan regex terhadap raw string)
supaya fenced code block, tabel, dan nesting list terdeteksi secara akurat terlepas
dari newline/bold/whitespace di sekitarnya.

Urutan output Segment menjaga urutan asli dokumen supaya reassembly benar.
"""

from __future__ import annotations

import re
from typing import List

from markdown_it import MarkdownIt

from src.segmentation.segment_types import Segment

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def _extract_inline_codes(text: str) -> List[Segment]:
    """
    Kembalikan list Segment inline_code yang ditemukan di *text*.
    Segmen ini tidak menggantikan prose — prose tetap dikembalikan terpisah,
    tapi inline_code diekstrak untuk diproses oleh code_block_handler.

    Catatan: pada reassembly, kita tetap memakai teks prose aslinya (yang sudah
    di-mask oleh prose_handler), jadi fungsi ini hanya digunakan untuk inspeksi
    apakah ada inline_code — penanganan inline_code di-delegate ke prose_handler
    karena Presidio akan memprosesnya sebagai teks biasa.
    """
    segments: List[Segment] = []
    for m in _INLINE_CODE_RE.finditer(text):
        segments.append(Segment(type="inline_code", content=m.group(1), meta={"match": m}))
    return segments


# ─────────────────────────────────────────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────────────────────────────────────────

def parse(markdown_text: str) -> List[Segment]:
    """
    Parse *markdown_text* menjadi list Segment berurutan.

    Tipe segmen yang dihasilkan:
    - "prose"      — semua teks naratif (paragraf, heading, list item, blockquote, dll.)
    - "code_block" — isi fenced code block (termasuk fence-nya untuk reassembly)
    - "table"      — blok tabel markdown lengkap (termasuk header dan separator row)

    Args:
        markdown_text: Teks markdown mentah.

    Returns:
        List[Segment] dalam urutan kemunculan di dokumen asli.
    """
    if not markdown_text:
        return []

    md = MarkdownIt().enable("table")
    tokens = md.parse(markdown_text)

    lines = markdown_text.splitlines(keepends=True)

    # Kumpulkan hanya top-level block ranges — hindari overlap dari child token
    # (thead_open, tr_open, dll. juga punya map tapi merupakan child dari table_open)
    block_ranges: List[dict] = []
    covered_up_to = -1  # baris terakhir yang sudah di-cover oleh block sebelumnya

    for token in tokens:
        if not token.map:
            continue
        start, end = token.map

        # Skip token yang line-range-nya sudah di-cover (child token dari block sebelumnya)
        if start < covered_up_to:
            continue

        block_ranges.append(
            {
                "type": token.type,
                "map": token.map,
                "info": (token.info or "").strip(),
                "content": token.content or "",
            }
        )
        covered_up_to = end

    if not block_ranges:
        return [Segment(type="prose", content=markdown_text)]

    segments = _build_segments(lines, block_ranges)
    return segments



def _raw_lines(lines: List[str], start: int, end: int) -> str:
    """Ambil baris raw dari dokumen (0-indexed, end exclusive)."""
    return "".join(lines[start:end])


def _build_segments(lines: List[str], block_ranges: List[dict]) -> List[Segment]:
    """
    Bangun list Segment dari block_ranges token.

    Celah (baris di antara block) dimasukkan ke segmen prose sebelumnya atau
    dijadikan prose tersendiri.
    """
    segments: List[Segment] = []
    total_lines = len(lines)
    prev_end = 0  # baris berikutnya yang belum diproses (0-indexed)

    for br in block_ranges:
        start, end = br["map"]

        # Baris sebelum blok ini → tambahkan ke prose buffer (whitespace/celah)
        if start > prev_end:
            gap = _raw_lines(lines, prev_end, start)
            if gap.strip():
                _append_or_merge_prose(segments, gap)

        token_type = br["type"]
        raw = _raw_lines(lines, start, end)

        if token_type == "fence":
            # ── code block ──────────────────────────────────────────────────
            lang = br["info"]
            segments.append(Segment(type="code_block", content=raw, meta={"lang": lang}))

        elif token_type == "table_open":
            # ── tabel ───────────────────────────────────────────────────────
            # markdown-it membagi tabel jadi beberapa token; kita sudah
            # rekonstruksi raw-nya dari baris sumber.
            segments.append(Segment(type="table", content=raw, meta={}))

        else:
            # ── prose (paragraf, heading, list, blockquote, hr, html, dll.) ─
            _append_or_merge_prose(segments, raw)

        prev_end = end

    # Sisa baris setelah blok terakhir
    if prev_end < total_lines:
        tail = _raw_lines(lines, prev_end, total_lines)
        if tail.strip():
            _append_or_merge_prose(segments, tail)

    return segments


def _append_or_merge_prose(segments: List[Segment], text: str) -> None:
    """
    Tambahkan teks ke segmen prose terakhir kalau ada, atau buat segmen baru.
    Ini menjaga prose yang terputus-putus oleh token heading/list tetap tergabung.
    """
    if segments and segments[-1].type == "prose":
        segments[-1].content += text
    else:
        segments.append(Segment(type="prose", content=text))


# ─────────────────────────────────────────────────────────────────────────────
# Reassembly
# ─────────────────────────────────────────────────────────────────────────────

def reassemble(segments: List[Segment]) -> str:
    """
    Gabungkan kembali list Segment menjadi satu string markdown.

    Urutan segmen dijaga — output harus identik dengan input kecuali bagian
    yang sudah di-mask.
    """
    return "".join(seg.content for seg in segments)
