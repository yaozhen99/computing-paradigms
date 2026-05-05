"""PasswordReader 口令输入层测试。

对应用例: TC-PW-01 ~ TC-PW-06
"""

from unittest.mock import patch

import pytest

from vault_cli.cli.password import PasswordReader, MIN_PASSWORD_LENGTH, MAX_CONFIRM_RETRIES
from vault_cli.errors import PasswordMismatchError, PasswordTooShortError


# ---------------------------------------------------------------------------
# TC-PW-01 ~ TC-PW-04: read_and_confirm
# ---------------------------------------------------------------------------

class TestPasswordReaderReadAndConfirm:
    """PasswordReader.read_and_confirm 测试组。"""

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_matching_passwords_return_bytes(self, mock_getpass):
        """TC-PW-01: 正常输入确认，两次一致返回 bytes。"""
        mock_getpass.side_effect = ["mypassword", "mypassword"]
        result = PasswordReader.read_and_confirm()
        assert result == b"mypassword"

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_password_too_short_raises_error(self, mock_getpass):
        """TC-PW-02: 口令过短。"""
        mock_getpass.side_effect = ["short", "short"]
        with pytest.raises(PasswordTooShortError) as exc_info:
            PasswordReader.read_and_confirm()
        assert exc_info.value.min_length == MIN_PASSWORD_LENGTH
        assert exc_info.value.actual_length == 5

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_mismatch_then_match_succeeds(self, mock_getpass):
        """TC-PW-03: 第一次不匹配，第二次匹配成功。"""
        # 第1轮: password="goodpass1", confirm="wrong1"
        # 第2轮: password="goodpass2", confirm="goodpass2"
        mock_getpass.side_effect = [
            "goodpass1", "wrong1",
            "goodpass2", "goodpass2",
        ]
        result = PasswordReader.read_and_confirm()
        assert result == b"goodpass2"

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_three_mismatches_raises_error(self, mock_getpass):
        """TC-PW-04: 三次不一致抛出 PasswordMismatchError。"""
        mock_getpass.side_effect = [
            "password1", "wrong1",
            "password2", "wrong2",
            "password3", "wrong3",
        ]
        with pytest.raises(PasswordMismatchError):
            PasswordReader.read_and_confirm()


# ---------------------------------------------------------------------------
# TC-PW-05 ~ TC-PW-06: read
# ---------------------------------------------------------------------------

class TestPasswordReaderRead:
    """PasswordReader.read 测试组。"""

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_read_returns_bytes(self, mock_getpass):
        """TC-PW-05: 单次读取返回 bytes。"""
        mock_getpass.return_value = "mypassword"
        result = PasswordReader.read()
        assert result == b"mypassword"

    @patch("vault_cli.cli.password.getpass.getpass")
    def test_read_empty_password(self, mock_getpass):
        """TC-PW-06: 空口令读取。"""
        mock_getpass.return_value = ""
        result = PasswordReader.read()
        assert result == b""
