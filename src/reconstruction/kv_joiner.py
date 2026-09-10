"""
kv_joiner.py — Gabungkan pola "key:\\n  value" (label dan value di baris terpisah)
jadi satu baris "key: value".

Kredensial yang di-export dari Confluence (mis. daftar VPN) sering ditulis dengan
label dan value di baris berbeda (kadang sebagai list item terpisah):

    - Username:
      vpnuser
    - Password:
      Vpn@ccess2024!

Recognizer kredensial kita (`credential_patterns.py`) butuh label dan value dalam
satu baris logis (`key: value`, `key=value`, dst.) supaya polanya match. Modul ini
menormalkan bentuk di atas jadi:

    Username: vpnuser
    Password: Vpn@ccess2024!

sebelum teks diserahkan ke Presidio Analyzer.
"""

from __future__ import annotations

import re

# Baris yang isinya HANYA "label:" (boleh didahului bullet "-"/"*" dan/atau
# dibungkus **bold**), tanpa value di baris yang sama.
_LABEL_ONLY_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:[-*]\s+)?\**(?P<key>[A-Za-z][A-Za-z0-9 _\-]{0,40}?)\**\s*:\s*$"
)


def join_multiline_kv(text: str) -> str:
    """
    Gabungkan baris "label:" yang diikuti baris value menjadi satu baris "label: value".

    Baris yang tidak cocok pola label-kosong dibiarkan apa adanya (termasuk baris
    yang sudah berbentuk "key: value" dalam satu baris — tidak diubah).

    Args:
        text: Teks mentah (mis. isi code block atau list item yang sudah di-strip
              dari marker markdown lain).

    Returns:
        Teks dengan pasangan label/value satu-baris digabung.
    """
    if not text:
        return text

    lines = text.splitlines()
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m = _LABEL_ONLY_RE.match(line)

        if m and i + 1 < n and lines[i + 1].strip():
            key = m.group("key").strip()
            value = lines[i + 1].strip()
            result.append(f"{m.group('indent')}{key}: {value}")
            i += 2
            continue

        result.append(line)
        i += 1

    return "\n".join(result)
