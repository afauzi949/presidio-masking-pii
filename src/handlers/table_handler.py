"""
table_handler.py — Handler untuk segmen tabel markdown.

Strategi:
1. Parse tabel markdown menjadi list of dict {column_name: value}.
2. Cocokkan nama kolom ke TABLE_SENSITIVE_COLUMNS (dari .env).
3. Mask seluruh value di kolom yang sensitive untuk semua row.
4. Reassemble kembali menjadi tabel markdown yang valid.

Reassembly menjaga lebar kolom (padding) supaya tabel tetap readable.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.config.settings import settings

# ─────────────────────────────────────────────────────────────────────────────
# Internal: parse tabel markdown
# ─────────────────────────────────────────────────────────────────────────────

def _split_pipe_row(line: str) -> List[str]:
    """
    Split baris tabel markdown berdasarkan pipe (|).
    Menghapus leading/trailing pipe dan whitespace tiap cell.
    """
    # Hapus leading/trailing pipe dan whitespace
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
        headers: list nama kolom dari baris header
        separator_cells: raw cell separator (untuk reconstruct)
        data_rows: list of list[str], satu list per row
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
            # Pad / trim supaya panjang sama dengan header
            while len(cells) < len(headers):
                cells.append("")
            data_rows.append(cells[: len(headers)])

    return headers, separator_cells, data_rows


def _is_sensitive_column(col_name: str) -> bool:
    """Return True kalau nama kolom ada di TABLE_SENSITIVE_COLUMNS (substring match)."""
    col_lower = col_name.lower().strip()
    return any(hint in col_lower for hint in settings.table_sensitive_columns_list)


def _mask_value(value: str) -> str:
    """Redact penuh nilai sensitif."""
    return "<REDACTED>"


def _build_row(cells: List[str], col_widths: List[int]) -> str:
    """Bangun satu baris tabel dengan padding untuk alignment."""
    padded = [cell.ljust(col_widths[i]) for i, cell in enumerate(cells)]
    return "| " + " | ".join(padded) + " |"


def _build_separator(separator_cells: Optional[List[str]], col_widths: List[int]) -> str:
    """Bangun baris separator tabel."""
    if separator_cells:
        # Pertahankan alignment indicator (:---:) tapi sesuaikan lebar
        sep_cells = []
        for i, cell in enumerate(separator_cells):
            w = col_widths[i]
            if cell.startswith(":") and cell.endswith(":"):
                sep_cells.append(":" + "-" * (w - 2) + ":")
            elif cell.startswith(":"):
                sep_cells.append(":" + "-" * (w - 1))
            elif cell.endswith(":"):
                sep_cells.append("-" * (w - 1) + ":")
            else:
                sep_cells.append("-" * w)
        return "| " + " | ".join(sep_cells) + " |"
    else:
        return "| " + " | ".join("-" * w for w in col_widths) + " |"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def mask(raw_table: str) -> str:
    """
    Mask tabel markdown: redact value di kolom sensitif.

    Args:
        raw_table: String tabel markdown mentah (termasuk header dan separator).

    Returns:
        String tabel markdown ter-mask, tetap valid markdown.
    """
    if not raw_table or not raw_table.strip():
        return raw_table

    headers, separator_cells, data_rows = _parse_table(raw_table)

    if not headers:
        return raw_table

    # Tentukan kolom mana yang sensitif
    sensitive_indices = {
        i for i, col in enumerate(headers) if _is_sensitive_column(col)
    }

    # Mask value di kolom sensitif
    masked_rows: List[List[str]] = []
    for row in data_rows:
        masked_row = [
            _mask_value(cell) if (i in sensitive_indices and cell.strip()) else cell
            for i, cell in enumerate(row)
        ]
        masked_rows.append(masked_row)

    # Hitung lebar kolom (max dari semua baris termasuk header)
    all_rows = [headers] + masked_rows
    col_widths = [
        max(len(row[i]) for row in all_rows if i < len(row))
        for i in range(len(headers))
    ]
    # Minimal lebar 3 supaya separator --- valid
    col_widths = [max(w, 3) for w in col_widths]

    # Reassemble
    output_lines: List[str] = []
    output_lines.append(_build_row(headers, col_widths))
    output_lines.append(_build_separator(separator_cells, col_widths))
    for row in masked_rows:
        output_lines.append(_build_row(row, col_widths))

    # Pertahankan trailing newline kalau ada
    result = "\n".join(output_lines)
    if raw_table.endswith("\n"):
        result += "\n"
    return result
