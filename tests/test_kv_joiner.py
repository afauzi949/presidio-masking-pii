"""
test_kv_joiner.py — Unit test untuk reconstruction.kv_joiner.

Independen dari Presidio — hanya menguji transformasi teks.
"""

from __future__ import annotations

from src.reconstruction.kv_joiner import join_multiline_kv


class TestJoinMultilineKV:
    def test_empty_string(self):
        assert join_multiline_kv("") == ""

    def test_simple_label_value_pair(self):
        result = join_multiline_kv("Password:\nVpn@ccess2024!")
        assert result == "Password: Vpn@ccess2024!"

    def test_vpn_multiline_credentials_as_list(self):
        """Kasus VPN config: label & value di bullet terpisah."""
        text = "- Username:\n  vpnuser\n- Password:\n  Vpn@ccess2024!\n"
        result = join_multiline_kv(text)
        assert "Username: vpnuser" in result
        assert "Password: Vpn@ccess2024!" in result

    def test_bold_label_joined(self):
        result = join_multiline_kv("**Password**:\nVpn@ccess2024!")
        assert result == "Password: Vpn@ccess2024!"

    def test_already_single_line_untouched(self):
        result = join_multiline_kv("password: alreadyOneLine")
        assert result == "password: alreadyOneLine"

    def test_label_without_colon_not_joined(self):
        """Baris yang bukan pola 'label:' murni dibiarkan apa adanya."""
        text = "Ini paragraf biasa.\nBukan label."
        assert join_multiline_kv(text) == text

    def test_label_at_end_without_value_line_untouched(self):
        """Label: di baris terakhir tanpa baris value sesudahnya — dibiarkan."""
        text = "Password:"
        assert join_multiline_kv(text) == "Password:"

    def test_mixed_content(self):
        text = "APP_NAME=MyApp\nUsername:\nadmin\nAPP_VERSION=1.0\n"
        result = join_multiline_kv(text)
        assert "APP_NAME=MyApp" in result
        assert "Username: admin" in result
        assert "APP_VERSION=1.0" in result
