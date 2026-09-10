"""
segment_types.py — Dataclass untuk merepresentasikan satu segmen dokumen markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal

SegmentType = Literal["prose", "code_block", "table", "inline_code"]


@dataclass
class Segment:
    """
    Satu segmen dari dokumen markdown setelah parsing.

    Attributes:
        type:    Kategori segmen — "prose", "code_block", "table", atau "inline_code".
        content: Teks mentah segmen (termasuk delimiter aslinya seperti fence ``` untuk
                 code block atau pipe | untuk tabel).
        meta:    Metadata tambahan, mis. {"lang": "python"} untuk code block.
    """

    type: SegmentType
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Convenience helpers                                                  #
    # ------------------------------------------------------------------ #

    @property
    def lang(self) -> str:
        """Shortcut untuk bahasa code block (lowercase). Kosong kalau bukan code_block."""
        return self.meta.get("lang", "").lower()
