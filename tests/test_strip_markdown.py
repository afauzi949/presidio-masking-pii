"""
test_strip_markdown.py — Unit test untuk reconstruction.strip_markdown.
"""

from __future__ import annotations

from src.reconstruction.strip_markdown import strip_markdown


class TestStripMarkdown:
    def test_empty_string(self):
        assert strip_markdown("") == ""

    def test_plain_paragraph(self):
        result = strip_markdown("Hello world, this is a paragraph.")
        assert "Hello world, this is a paragraph." in result

    def test_heading_marker_removed(self):
        result = strip_markdown("# Heading 1")
        assert "Heading 1" in result
        assert "#" not in result

    def test_bold_marker_removed_content_kept(self):
        result = strip_markdown("Hubungi **John Smith** untuk info.")
        assert "John Smith" in result
        assert "**" not in result

    def test_inline_code_content_kept_backtick_removed(self):
        result = strip_markdown("Gunakan `token=abc123def456` sebelum deploy.")
        assert "token=abc123def456" in result
        assert "`" not in result

    def test_list_marker_removed(self):
        result = strip_markdown("- item satu\n- item dua\n")
        assert "item satu" in result
        assert "item dua" in result
        assert "- item" not in result

    def test_email_content_preserved(self):
        result = strip_markdown("Hubungi saya di john.doe@example.com untuk info.")
        assert "john.doe@example.com" in result

    def test_multi_block_separated_by_newline(self):
        result = strip_markdown("# Heading\n\nParagraf pertama.\n\nParagraf kedua.\n")
        blocks = [b for b in result.split("\n") if b.strip()]
        assert "Heading" in blocks
        assert "Paragraf pertama." in blocks
        assert "Paragraf kedua." in blocks
