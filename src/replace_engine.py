"""
replace_engine.py — Kumpulkan literal value dari hasil Presidio Analyzer, lalu
replace langsung ke markdown ASLI (bukan ke teks rekonstruksi).

Lihat plan.md bagian "Risiko yang Wajib Ditangani" untuk rasional dua langkah
di bawah:
    1. Value pendek/generic di-skip (Risiko #1) — mencegah replace-balik salah
       sasaran ke tempat lain di dokumen yang kebetulan mengandung string pendek
       yang sama.
    2. Replace berurutan dari value TERPANJANG dulu (Risiko #2) — supaya value
       yang merupakan substring dari value lain (mis. "admin" di dalam
       "admin_prod") tidak rusak duluan sebelum sempat ke-replace utuh.
"""

from __future__ import annotations

from typing import List

# Value literal di bawah panjang ini di-skip — terlalu pendek/generic untuk
# di-replace secara aman ke seluruh dokumen tanpa risiko salah sasaran.
MIN_VALUE_LENGTH = 4

DEFAULT_PLACEHOLDER = "<REDACTED>"


def collect_literal_values(
    text: str,
    results: List,
    min_length: int = MIN_VALUE_LENGTH,
) -> List[str]:
    """
    Ambil literal substring value dari hasil `AnalyzerEngine.analyze()`.

    Args:
        text:        Teks rekonstruksi yang dianalisis (bukan markdown asli) —
                     `results[i].start/end` adalah index ke teks ini.
        results:     List `RecognizerResult` dari Presidio.
        min_length:  Panjang minimum value supaya ikut di-replace (Risiko #1).

    Returns:
        List literal value, sudah dedup, diurutkan DESC by length (Risiko #2).
    """
    values = set()
    for r in results:
        literal = text[r.start:r.end].strip()
        if len(literal) < min_length:
            continue
        values.add(literal)

    return sorted(values, key=len, reverse=True)


def replace_into_original(
    raw_markdown: str,
    values: List[str],
    placeholder: str = DEFAULT_PLACEHOLDER,
) -> str:
    """
    Replace tiap literal value (persis, case-sensitive) di markdown asli dengan
    placeholder seragam.

    Kalau suatu literal value tidak ditemukan persis di markdown asli (mis.
    karena proses rekonstruksi mengubah bentuknya), replace untuk value itu
    dilewati diam-diam — `str.replace` tidak melakukan apa-apa kalau substring
    tidak ada, jadi bagian dokumen lain tidak terpengaruh.

    Args:
        raw_markdown: Dokumen markdown asli, utuh.
        values:       List literal value dari `collect_literal_values`, HARUS
                      sudah terurut DESC by length.
        placeholder:  Teks pengganti, seragam untuk semua entity.

    Returns:
        Markdown asli dengan value sensitif tergantikan.
    """
    result = raw_markdown
    for value in values:
        if value:
            result = result.replace(value, placeholder)
    return result
