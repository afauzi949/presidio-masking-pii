"""
strip_markdown.py — Ekstrak plain text dari segmen prose.

Memanfaatkan token AST bawaan markdown-it-py (bukan regex manual) supaya markup
(**, `, #, -, >, dll.) hilang secara akurat terlepas dari kombinasi/nesting-nya,
sementara isi teks (termasuk isi inline code `seperti_ini`) tetap dipertahankan
untuk dianalisis Presidio.

Bagian dari skema "restrukturisasi lalu replace-balik" — lihat plan.md.
"""

from __future__ import annotations

from markdown_it import MarkdownIt

_MD = MarkdownIt()

# Tipe child token dalam "inline" token yang isinya benar-benar teks yang mau
# dipertahankan. Tipe lain (strong_open/close, em_open/close, link_open/close,
# html_inline, dst.) adalah markup murni dan sengaja diabaikan.
_TEXT_CHILD_TYPES = {"text", "code_inline"}
_BREAK_CHILD_TYPES = {"softbreak", "hardbreak"}


def strip_markdown(text: str) -> str:
    """
    Ubah satu segmen prose markdown menjadi plain text.

    Setiap blok (paragraf/heading/list item/dst.) direpresentasikan sebagai satu
    baris di output, dipisah "\\n" — supaya konteks antar blok tidak nyampur saat
    dianalisis Presidio, tapi tetap ringkas untuk hasil deteksi yang presisi.

    Args:
        text: Potongan markdown mentah (segmen bertipe "prose" dari markdown_parser).

    Returns:
        Plain text tanpa markup, siap digabung ke teks rekonstruksi.
    """
    if not text or not text.strip():
        return text or ""

    tokens = _MD.parse(text)
    blocks: list[str] = []

    for token in tokens:
        if token.type != "inline" or not token.children:
            continue

        pieces: list[str] = []
        for child in token.children:
            if child.type in _TEXT_CHILD_TYPES:
                pieces.append(child.content)
            elif child.type in _BREAK_CHILD_TYPES:
                pieces.append("\n")

        block_text = "".join(pieces).strip()
        if block_text:
            blocks.append(block_text)

    return "\n".join(blocks)
