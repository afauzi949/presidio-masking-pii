"""
code_block_to_lines.py — Normalisasi isi fenced code block jadi baris "key: value"
yang bisa dibaca Presidio, tanpa masking langsung (lihat plan.md bagian 0).

Strategi per bahasa:
- JSON     → di-parse betulan (json.loads), lalu diratakan (flatten) jadi baris
             "key: value" per pasangan — sintaks JSON asli (tanda kutip, koma)
             bikin pola "key: value" recognizer tidak match kalau dibiarkan mentah.
- Lainnya (env, yaml, ini, conf, python, dst.) → sudah pada dasarnya berbentuk
  "key: value"/"key=value" per baris (atau tidak terstruktur sama sekali, mis.
  kode Python) — cukup lewatkan fence-nya saja, lalu jalankan `join_multiline_kv`
  untuk menggabungkan pola label/value yang terpisah baris (mis. gaya VPN config).

Delimiter fence (``` ... ```) TIDAK disertakan di output — teks hasil modul ini
cuma dipakai untuk dianalisis Presidio, bukan untuk ditampilkan kembali sebagai
markdown (masking terjadi lewat replace literal value ke markdown ASLI, lihat
`src/replace_engine.py` dan `src/masker.py`).
"""

from __future__ import annotations

import json
from typing import Optional, Tuple

from src.reconstruction.kv_joiner import join_multiline_kv

# ─────────────────────────────────────────────────────────────────────────────
# Fence delimiter parser
# ─────────────────────────────────────────────────────────────────────────────


def _split_fence(raw: str) -> Tuple[str, str, str]:
    """
    Pisahkan raw code block menjadi (opening_fence, content, closing_fence).
    """
    lines = raw.splitlines(keepends=True)
    if len(lines) < 2:
        return "", raw, ""

    open_fence = lines[0]
    close_fence = lines[-1] if lines[-1].strip().startswith(("```", "~~~")) else ""
    if close_fence:
        content = "".join(lines[1:-1])
    else:
        content = "".join(lines[1:])

    return open_fence, content, close_fence


# ─────────────────────────────────────────────────────────────────────────────
# JSON flatten
# ─────────────────────────────────────────────────────────────────────────────


def _flatten_json(content: str) -> str:
    """
    Parse JSON dan ratakan jadi baris "key: value" per pasangan (nested key
    dilewatkan tanpa prefix path — cukup nama key paling dalam, karena yang
    dicek recognizer cuma nama key-nya, bukan posisinya di struktur).

    Kalau parsing gagal, kembalikan konten apa adanya (fallback).
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return content

    lines: list[str] = []

    def _walk(obj, key: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, k)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, key)
        else:
            if key and obj not in (None, ""):
                lines.append(f"{key}: {obj}")

    _walk(data)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def code_block_to_lines(raw_block: str, lang: Optional[str] = None) -> str:
    """
    Normalisasi konten fenced code block jadi teks yang siap dianalisis Presidio.

    Args:
        raw_block: String mentah code block termasuk opening/closing fence.
        lang:      Bahasa block (mis. "python", "env", "json"). Boleh None/kosong.

    Returns:
        Teks konten (tanpa fence), siap digabung ke teks rekonstruksi dokumen.
    """
    if not raw_block:
        return ""

    _open_fence, content, _close_fence = _split_fence(raw_block)

    lang_lower = (lang or "").lower().strip()
    if lang_lower == "json":
        content = _flatten_json(content)

    return join_multiline_kv(content)
