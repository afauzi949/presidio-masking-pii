"""
test_markdown_parser.py — Unit test untuk segmentasi markdown.

Memastikan segmentasi benar untuk:
- Paragraf biasa (prose)
- Fenced code block (code_block)
- Tabel markdown (table)
- Campuran prose + code block + tabel dalam satu dokumen
"""

from __future__ import annotations

import pytest

from src.segmentation import markdown_parser
from src.segmentation.segment_types import Segment


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def types_of(segments: list) -> list:
    return [s.type for s in segments]


def content_of(segments: list, seg_type: str) -> list:
    return [s.content for s in segments if s.type == seg_type]


# ─────────────────────────────────────────────────────────────────────────────
# Prose tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProseSegmentation:
    def test_simple_paragraph(self):
        md = "Hello world, this is a paragraph."
        segments = markdown_parser.parse(md)
        assert any(s.type == "prose" for s in segments)

    def test_heading_is_prose(self):
        md = "# Heading 1\n\nSome paragraph text."
        segments = markdown_parser.parse(md)
        prose_contents = content_of(segments, "prose")
        combined = "".join(prose_contents)
        assert "Heading" in combined or "paragraph" in combined

    def test_empty_string_returns_empty(self):
        assert markdown_parser.parse("") == []

    def test_prose_with_bold_and_newline(self):
        """Password yang dipisah newline di prose harus tetap jadi satu segmen prose."""
        md = "Konfigurasi server:\n\nUsername: admin\nPassword: mySecret123\n"
        segments = markdown_parser.parse(md)
        assert any(s.type == "prose" for s in segments)
        combined = "".join(s.content for s in segments if s.type == "prose")
        assert "Password" in combined


# ─────────────────────────────────────────────────────────────────────────────
# Code block tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCodeBlockSegmentation:
    def test_basic_code_block_detected(self):
        md = "Some text.\n\n```python\nprint('hello')\n```\n"
        segments = markdown_parser.parse(md)
        assert "code_block" in types_of(segments)

    def test_code_block_lang_captured(self):
        md = "```env\nDB_PASSWORD=secret\n```\n"
        segments = markdown_parser.parse(md)
        code_segs = [s for s in segments if s.type == "code_block"]
        assert code_segs, "Harus ada code_block segment"
        assert code_segs[0].lang == "env"

    def test_code_block_without_lang(self):
        md = "```\nsome content\n```\n"
        segments = markdown_parser.parse(md)
        code_segs = [s for s in segments if s.type == "code_block"]
        assert code_segs
        assert code_segs[0].lang == ""

    def test_code_block_content_preserved(self):
        content = "API_KEY=AbCdEfGhIjKlMnOp\n"
        md = f"```env\n{content}```\n"
        segments = markdown_parser.parse(md)
        code_segs = [s for s in segments if s.type == "code_block"]
        assert any("API_KEY" in s.content for s in code_segs)

    def test_multiple_code_blocks(self):
        md = (
            "Text sebelum.\n\n"
            "```python\nprint('hi')\n```\n\n"
            "Text tengah.\n\n"
            "```env\nDB_PASS=secret\n```\n"
        )
        segments = markdown_parser.parse(md)
        code_segs = [s for s in segments if s.type == "code_block"]
        assert len(code_segs) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Table tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTableSegmentation:
    def test_basic_table_detected(self):
        md = "| Name | Email |\n|------|-------|\n| Alice | alice@example.com |\n"
        segments = markdown_parser.parse(md)
        assert "table" in types_of(segments)

    def test_table_with_sensitive_column(self):
        md = (
            "| Service | Password |\n"
            "|---------|----------|\n"
            "| DB | mySecret |\n"
        )
        segments = markdown_parser.parse(md)
        table_segs = [s for s in segments if s.type == "table"]
        assert table_segs
        assert "Password" in table_segs[0].content


# ─────────────────────────────────────────────────────────────────────────────
# Mixed document tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMixedDocument:
    def test_mixed_prose_code_table(self):
        md = (
            "# Konfigurasi Server\n\n"
            "Berikut detail koneksi database:\n\n"
            "```env\n"
            "DB_HOST=localhost\n"
            "DB_PASSWORD=s3cr3t\n"
            "```\n\n"
            "| Service | Token |\n"
            "|---------|-------|\n"
            "| API GW  | abc123xyz |\n\n"
            "Hubungi admin untuk pertanyaan lebih lanjut.\n"
        )
        segments = markdown_parser.parse(md)
        seg_types = types_of(segments)

        assert "prose" in seg_types
        assert "code_block" in seg_types
        assert "table" in seg_types

    def test_reassembly_preserves_non_sensitive_content(self):
        md = "Hello world.\n"
        segments = markdown_parser.parse(md)
        reassembled = markdown_parser.reassemble(segments)
        assert "Hello world" in reassembled

    def test_reassembly_order(self):
        """Reassembly harus mempertahankan urutan asli."""
        md = (
            "First paragraph.\n\n"
            "```\nsome code\n```\n\n"
            "Second paragraph.\n"
        )
        segments = markdown_parser.parse(md)
        reassembled = markdown_parser.reassemble(segments)
        assert reassembled.index("First") < reassembled.index("some code")
        assert reassembled.index("some code") < reassembled.index("Second")
