"""
code_block_handler.py — Handler untuk segmen fenced code block.

Strategi:
- Tidak menjalankan Presidio AnalyzerEngine berbasis NLP context (karena code
  block biasanya tidak punya kalimat context di sekitarnya).
- Untuk bahasa terstruktur (env, ini, yaml, json, toml, conf):
    → Parse key-value pair, cocokkan key ke CREDENTIAL_KEY_HINTS, mask value-nya.
- Untuk bahasa lain atau tanpa bahasa:
    → Jalankan credential PatternRecognizer langsung baris per baris (regex only,
       tanpa context boosting).

Delimiter fenced block (``` ... ```) dipertahankan di output supaya reassembly
menghasilkan markdown yang valid.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from src.config.settings import settings

# ─────────────────────────────────────────────────────────────────────────────
# Bahasa yang diperlakukan sebagai structured key-value
# ─────────────────────────────────────────────────────────────────────────────

_KV_LANGS = {"env", "ini", "toml", "conf", "cfg", "properties", "yaml", "yml", "json"}

# Regex untuk key=value atau key: value (env / ini style, dengan optional indent)
_KV_LINE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_\-.]*)(?P<sep>\s*[:=]\s*)(?P<value>.+)$"
)

# ─────────────────────────────────────────────────────────────────────────────
# Regex untuk deteksi credential langsung di baris kode (fallback)
# ─────────────────────────────────────────────────────────────────────────────

_CREDENTIAL_PATTERNS: List[re.Pattern] = [
    # password=value, passwd: value, secret=value
    re.compile(
        r"(?i)(password|passwd|pwd|secret)\s*[:=]\s*(\S+)"
    ),
    # DB connection URI
    re.compile(
        r"(?i)(postgresql|postgres|mysql|mongodb|mongo|redis|mssql|oracle|sqlite)"
        r"(?:\+\w+)?://\S+:\S+@\S+"
    ),
    # API key assignment (>=16 char value)
    re.compile(
        r"(?i)(api[_\-]?key|access[_\-]?key|token|secret[_\-]?key|auth[_\-]?token)"
        r"\s*[:=]\s*([A-Za-z0-9\-_.~+/]{16,})"
    ),
    # Bearer token
    re.compile(r"(?i)Bearer\s+([A-Za-z0-9\-_.~+/=]{20,})"),
    # IP:port
    re.compile(
        r"\b((?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
        r":\d{2,5})\b"
    ),
]


def _mask_value(value: str) -> str:
    """Redact penuh nilai sensitif."""
    return "<REDACTED>"


def _is_sensitive_key(key: str) -> bool:
    """Return True kalau key ada di CREDENTIAL_KEY_HINTS (case-insensitive)."""
    key_lower = key.lower().strip()
    return any(hint in key_lower for hint in settings.credential_key_hints_list)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing structured formats
# ─────────────────────────────────────────────────────────────────────────────

def _mask_kv_line(line: str) -> str:
    """
    Mask satu baris key=value / key: value (dengan optional leading indent).
    Kalau key sensitif → mask value.
    Kalau key tidak sensitif tapi value mengandung credential pattern → mask value.
    """
    m = _KV_LINE_RE.match(line.rstrip("\n"))
    if not m:
        return line
    indent = m.group("indent")
    key = m.group("key")
    sep = m.group("sep")
    value = m.group("value")
    if value.strip() in ("", '""', "''"):
        return line
    # 1. Key match langsung
    if _is_sensitive_key(key):
        masked = f"{indent}{key}{sep}{_mask_value(value)}"
        return masked + "\n" if line.endswith("\n") else masked
    # 2. Value match credential pattern (mis. DB URI di field db_url)
    masked_value = _apply_credential_patterns(value)
    if masked_value != value:
        masked = f"{indent}{key}{sep}{masked_value}"
        return masked + "\n" if line.endswith("\n") else masked
    return line


def _mask_json_content(content: str) -> str:
    """
    Parse JSON dan mask value untuk key yang sensitif.
    Kalau parsing gagal, fallback ke per-baris kv masking.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return _mask_lines_generic(content)

    def _recurse(obj):
        if isinstance(obj, dict):
            return {
                k: (_mask_value(str(v)) if _is_sensitive_key(k) and v not in (None, "", [], {}) else _recurse(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_recurse(item) for item in obj]
        return obj

    masked = _recurse(data)
    try:
        return json.dumps(masked, indent=2, ensure_ascii=False)
    except Exception:
        return content


def _mask_yaml_content(content: str) -> str:
    """
    Mask YAML: gunakan regex per baris untuk key: value pattern.
    Tidak meng-import PyYAML supaya dependency tetap minimal.
    """
    result_lines = []
    for line in content.splitlines(keepends=True):
        result_lines.append(_mask_kv_line(line))
    return "".join(result_lines)


def _mask_lines_generic(content: str) -> str:
    """
    Mask per-baris: coba KV pattern dulu, lalu regex credential langsung.
    """
    result_lines = []
    for line in content.splitlines(keepends=True):
        # 1. Coba KV line masking (includes indented yaml-like lines)
        if _KV_LINE_RE.match(line.rstrip("\n")):
            result_lines.append(_mask_kv_line(line))
            continue

        # 2. Regex credential langsung
        masked_line = _apply_credential_patterns(line)
        result_lines.append(masked_line)

    return "".join(result_lines)


def _apply_credential_patterns(line: str) -> str:
    """Apply all credential regex patterns to a single line."""
    masked_line = line
    for pattern in _CREDENTIAL_PATTERNS:
        def _replacer(m: re.Match, _p=pattern) -> str:
            full = m.group(0)
            # Untuk pola dengan grup value terpisah — redact grup terakhir
            if m.lastindex and m.lastindex >= 2:
                value_part = m.group(m.lastindex)
                return full[:m.start(m.lastindex) - m.start()] + "<REDACTED>"
            # Pola single grup atau no group — redact seluruh match
            # Untuk DB URI: redact seluruh URI
            return "<REDACTED>"

        masked_line = pattern.sub(_replacer, masked_line)
    return masked_line


# ─────────────────────────────────────────────────────────────────────────────
# Fence delimiter parser
# ─────────────────────────────────────────────────────────────────────────────

def _split_fence(raw: str) -> Tuple[str, str, str]:
    """
    Pisahkan raw code block menjadi (opening_fence, content, closing_fence).

    Opening fence: baris pertama yang dimulai dengan ``` atau ~~~.
    Closing fence: baris terakhir yang matching.
    Content: semua baris di antaranya.
    """
    lines = raw.splitlines(keepends=True)
    if len(lines) < 2:
        return "", raw, ""

    open_fence = lines[0]
    close_fence = lines[-1] if lines[-1].strip().startswith(("```", "~~~")) else ""
    if close_fence:
        content = "".join(lines[1:-1])
    else:
        # Tidak ada closing fence yang teridentifikasi — anggap konten semua kecuali baris pertama
        content = "".join(lines[1:])

    return open_fence, content, close_fence


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def mask(raw_block: str, lang: Optional[str] = None) -> str:
    """
    Mask konten fenced code block.

    Args:
        raw_block: String mentah code block termasuk opening/closing fence.
        lang:      Bahasa block (mis. "python", "env", "yaml"). Digunakan untuk
                   memilih strategi parsing. Boleh None atau kosong.

    Returns:
        String code block ter-mask, dengan fence tetap utuh.
    """
    if not raw_block:
        return raw_block

    open_fence, content, close_fence = _split_fence(raw_block)

    lang_lower = (lang or "").lower().strip()

    if lang_lower in ("json",):
        masked_content = _mask_json_content(content)
    elif lang_lower in ("yaml", "yml"):
        masked_content = _mask_yaml_content(content)
    elif lang_lower in _KV_LANGS:
        # env / ini / toml / conf / properties
        masked_content = "".join(
            _mask_kv_line(line) for line in content.splitlines(keepends=True)
        )
    else:
        # Bahasa lain atau tanpa bahasa — regex per baris
        masked_content = _mask_lines_generic(content)

    return open_fence + masked_content + close_fence
