"""CLI 入口和错误体系测试。

对应用例: TC-MAIN-01 ~ TC-MAIN-06, TC-ERR-01 ~ TC-ERR-03
"""

from unittest.mock import patch

import pytest

from vault_cli.cli.main import main, build_parser
from vault_cli.cli.exit_codes import ExitCode
from vault_cli.errors import (
    VaultError,
    KeystoreNotInitializedError,
    KeystoreAlreadyInitializedError,
    AuthenticationError,
    VaultFileFormatError,
    VaultFileNotFoundError,
    PasswordTooShortError,
    PasswordMismatchError,
    InvalidFileError,
)


# ---------------------------------------------------------------------------
# TC-MAIN-01 ~ TC-MAIN-06: CLI 入口
# ---------------------------------------------------------------------------

class TestCLIMain:
    """CLI main 入口测试组。"""

    def test_no_subcommand_returns_argument_error(self):
        """TC-MAIN-01: 无子命令返回 ARGUMENT_ERROR。"""
        result = main([])
        assert result == ExitCode.ARGUMENT_ERROR

    def test_version_flag(self, capsys):
        """TC-MAIN-02: --version 输出版本号。"""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_parse_init_command(self, tmp_path):
        """TC-MAIN-03: 解析 init 子命令。"""
        vault_dir = tmp_path / ".vault"
        with patch("vault_cli.cli.commands.init.KeyManager") as MockKM:
            MockKM.is_initialized.return_value = False
            MockKM.init_keystore.return_value = type("Config", (), {
                "salt_length": 16,
                "algorithm": "AES-256-GCM",
                "kdf": "PBKDF2-SHA256",
                "iterations": 600000,
            })()
            result = main(["init", "--vault-dir", str(vault_dir)])
        assert result == ExitCode.SUCCESS

    def test_parse_lock_command(self, tmp_path):
        """TC-MAIN-04: 解析 lock 子命令。"""
        vault_dir = tmp_path / ".vault"
        from vault_cli.keymgr.manager import KeyManager
        KeyManager.init_keystore(vault_dir)
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            result = main(["lock", str(f), "--vault-dir", str(vault_dir)])
        assert result == ExitCode.SUCCESS

    def test_parse_unlock_command(self, tmp_path):
        """TC-MAIN-05: 解析 unlock 子命令。"""
        vault_dir = tmp_path / ".vault"
        from vault_cli.keymgr.manager import KeyManager
        KeyManager.init_keystore(vault_dir)
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            main(["lock", str(f), "--keep", "--vault-dir", str(vault_dir)])
        vault_path = tmp_path / "test.txt.vault"
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            result = main(["unlock", str(vault_path), "--vault-dir", str(vault_dir)])
        assert result == ExitCode.SUCCESS

    def test_parse_list_command(self, tmp_path):
        """TC-MAIN-06: 解析 list 子命令。"""
        result = main(["list", "--dir", str(tmp_path)])
        assert result == ExitCode.SUCCESS


# ---------------------------------------------------------------------------
# TC-ERR-01 ~ TC-ERR-03: 错误体系
# ---------------------------------------------------------------------------

class TestErrorHierarchy:
    """错误体系测试组。"""

    def test_password_too_short_attributes(self):
        """TC-ERR-01: PasswordTooShortError 属性。"""
        err = PasswordTooShortError(min_length=8, actual_length=3)
        assert err.min_length == 8
        assert err.actual_length == 3
        assert "3" in str(err)

    def test_all_errors_inherit_from_vault_error(self):
        """TC-ERR-02: 所有自定义异常均继承自 VaultError。"""
        error_classes = [
            KeystoreNotInitializedError,
            KeystoreAlreadyInitializedError,
            AuthenticationError,
            VaultFileFormatError,
            VaultFileNotFoundError,
            PasswordTooShortError,
            PasswordMismatchError,
            InvalidFileError,
        ]
        for cls in error_classes:
            assert issubclass(cls, VaultError), f"{cls.__name__} 不继承自 VaultError"

    def test_exit_code_values(self):
        """TC-ERR-03: ExitCode 枚举值正确。"""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.ARGUMENT_ERROR == 2
        assert ExitCode.CRYPTO_ERROR == 3
        assert ExitCode.KEYSTORE_NOT_INITIALIZED == 4
