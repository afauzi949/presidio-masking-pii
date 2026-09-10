"""
table_to_sentence.py — Ubah tabel markdown mentah jadi representasi teks
"Header: value" per baris, supaya bisa dianalisis Presidio sebagai teks biasa.

Ini BUKAN masking langsung berdasarkan nama kolom (pendekatan lama di
`table_handler.py`, lihat plan.md bagian 0) — modul ini cuma mengubah bentuk
data, deteksi kredensial-nya sendiri tetap satu sumber kebenaran: Presidio
Analyzer (regex + context word + custom recognizer), dijalankan belakangan atas
seluruh teks rekonstruksi oleh `masker.py`.

Setiap field dipisah baris ("Header: value"), BUKAN digabung jadi satu kalimat
dengan titik ("Header: value. Header2: value2.") — supaya karakter pemisah "."
tidak ikut ter-capture sebagai bagian dari value oleh recognizer kredensial
(nilai berhenti di batas whitespace/baris, bukan di titik yang kita tambahkan
sendiri). Baris kosong memisahkan antar-row supaya konteks antar baris tabel
tidak saling bocor ke context-word matching Presidio.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Parsing tabel markdown (dipakai juga dipola yang sama sebelumnya di
# table_handler.py — dipertahankan di sini karena table_handler.py sudah tidak
# ada, perannya digantikan modul ini)
# ─────────────────────────────────────────────────────────────────────────────


def _split_pipe_row(line: str) -> List[str]:
    """Split baris tabel markdown berdasarkan pipe (|), buang whitespace tiap cell."""
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator_row(cells: List[str]) -> bool:
    """Return True kalau baris adalah separator (---) row."""
    return all(re.fullmatch(r":?-+:?", c.strip()) for c in cells if c.strip())


def _parse_table(raw: str) -> Tuple[List[str], Optional[List[str]], List[List[str]]]:
    """
    Parse raw tabel markdown.

    Returns:
        (headers, separator_cells, data_rows)
    """
    lines = [l for l in raw.splitlines() if l.strip()]

    if not lines:
        return [], None, []

    headers = _split_pipe_row(lines[0])
    separator_cells: Optional[List[str]] = None
    data_rows: List[List[str]] = []

    for line in lines[1:]:
        cells = _split_pipe_row(line)
        if _is_separator_row(cells):
            separator_cells = cells
        else:
            while len(cells) < len(headers):
                cells.append("")
            data_rows.append(cells[: len(headers)])

    return headers, separator_cells, data_rows


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def table_to_sentence(raw_table: str) -> str:
    """
    Ubah tabel markdown mentah jadi teks "Header: value" per baris per field.

    Args:
        raw_table: String tabel markdown mentah (header + separator + data rows).

    Returns:
        Teks representasi tabel, siap digabung ke teks rekonstruksi dokumen.
        String kosong kalau tabel tidak valid/tidak ada header.
    """
    if not raw_table or not raw_table.strip():
        return ""

    headers, _separator, data_rows = _parse_table(raw_table)
    if not headers:
        return ""

    row_blocks: List[str] = []
    for row in data_rows:
        field_lines = [
            f"{header.strip()}: {value.strip()}"
            for header, value in zip(headers, row)
            if value.strip()
        ]
        if field_lines:
            row_blocks.append("\n".join(field_lines))

    return "\n\n".join(row_blocks)
