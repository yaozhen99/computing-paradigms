"""CLI 子命令层测试。

对应用例: TC-CLI-01 ~ TC-CLI-25
通过直接调用 cmd_* 函数并 Mock getpass 来测试。
"""

from unittest.mock import patch

import pytest

from vault_cli.cli.commands.init import cmd_init
from vault_cli.cli.commands.lock import cmd_lock
from vault_cli.cli.commands.unlock import cmd_unlock
from vault_cli.cli.commands.list import cmd_list
from vault_cli.cli.exit_codes import ExitCode
from vault_cli.keymgr.manager import KeyManager
from vault_cli.crypto.service import CryptoService
from vault_cli.fileio.vault_io import VaultFileIO
import struct


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _setup_keystore(tmp_path):
    """初始化密钥库并返回 vault_dir。"""
    vault_dir = tmp_path / ".vault"
    cmd_init(vault_dir=vault_dir)
    return vault_dir


def _create_test_file(tmp_path, name="secret.txt", content=b"hello world"):
    """创建测试文件并返回路径。"""
    f = tmp_path / name
    f.write_bytes(content)
    return f


def _encrypt_file(tmp_path, vault_dir, filename="secret.txt", password="testpassword"):
    """加密一个文件并返回 .vault 路径。"""
    file_path = _create_test_file(tmp_path, filename)
    with patch("vault_cli.cli.password.getpass.getpass", side_effect=[password, password]):
        result = cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
    assert result == ExitCode.SUCCESS
    return file_path, file_path.parent / (filename + ".vault")


# ---------------------------------------------------------------------------
# TC-CLI-01 ~ TC-CLI-03: vault init
# ---------------------------------------------------------------------------

class TestCmdInit:
    """cmd_init 测试组。"""

    def test_first_init_success(self, tmp_path):
        """TC-CLI-01: 首次初始化返回 SUCCESS。"""
        vault_dir = tmp_path / ".vault"
        result = cmd_init(vault_dir=vault_dir)
        assert result == ExitCode.SUCCESS
        assert (vault_dir / "salt.bin").is_file()
        assert (vault_dir / "config.json").is_file()

    def test_duplicate_init_idempotent(self, tmp_path):
        """TC-CLI-02: 重复初始化幂等返回 SUCCESS。"""
        vault_dir = tmp_path / ".vault"
        cmd_init(vault_dir=vault_dir)
        result = cmd_init(vault_dir=vault_dir)
        assert result == ExitCode.SUCCESS

    def test_init_default_path(self, tmp_path):
        """TC-CLI-03: 默认路径初始化（使用 ~/.vault/）。"""
        # 此处仅验证不传 vault_dir 不崩溃
        # 由于默认路径是真实 home 目录，为避免污染，使用 Mock
        with patch("vault_cli.cli.commands.init.KeyManager") as MockKM:
            MockKM.is_initialized.return_value = True
            result = cmd_init()
            assert result == ExitCode.SUCCESS


# ---------------------------------------------------------------------------
# TC-CLI-04 ~ TC-CLI-11: vault lock
# ---------------------------------------------------------------------------

class TestCmdLock:
    """cmd_lock 测试组。"""

    def test_lock_normal(self, tmp_path):
        """TC-CLI-04: 正常加密返回 SUCCESS。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            result = cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert result == ExitCode.SUCCESS
        assert VaultFileIO.resolve_vault_path(file_path).exists()

    def test_lock_default_removes_original(self, tmp_path):
        """TC-CLI-05: 加密后默认删除原文件。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert not file_path.exists()
        assert VaultFileIO.resolve_vault_path(file_path).exists()

    def test_lock_keep_preserves_original(self, tmp_path):
        """TC-CLI-06: --keep 保留原文件。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
        assert file_path.exists()
        assert VaultFileIO.resolve_vault_path(file_path).exists()

    def test_lock_keystore_not_initialized(self, tmp_path):
        """TC-CLI-07: 密钥库未初始化返回退出码 4。"""
        vault_dir = tmp_path / ".vault"
        file_path = _create_test_file(tmp_path)
        result = cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert result == ExitCode.KEYSTORE_NOT_INITIALIZED

    def test_lock_file_not_found(self, tmp_path):
        """TC-CLI-08: 文件不存在返回退出码 2。"""
        vault_dir = _setup_keystore(tmp_path)
        missing = tmp_path / "nonexistent.txt"
        result = cmd_lock(file_path=missing, vault_dir=vault_dir)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_lock_directory_path(self, tmp_path):
        """TC-CLI-09: 路径为目录返回退出码 2。"""
        vault_dir = _setup_keystore(tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = cmd_lock(file_path=subdir, vault_dir=vault_dir)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_lock_password_too_short(self, tmp_path):
        """TC-CLI-10: 口令过短返回退出码 1。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["short", "short"]):
            result = cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert result == ExitCode.GENERAL_ERROR

    def test_lock_password_mismatch_three_times(self, tmp_path):
        """TC-CLI-11: 三次口令不匹配返回退出码 1。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=[
            "password1", "wrong1",
            "password2", "wrong2",
            "password3", "wrong3",
        ]):
            result = cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert result == ExitCode.GENERAL_ERROR

    def test_lock_original_delete_failure_returns_general_error(self, tmp_path):
        """TC-CLI-26: 原文件删除失败返回退出码 1（GENERAL_ERROR）而非 3（CRYPTO_ERROR）。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            with patch("vault_cli.cli.commands.lock.VaultFileIO.remove_original", side_effect=OSError("Permission denied")):
                result = cmd_lock(file_path=file_path, vault_dir=vault_dir)
        assert result == ExitCode.GENERAL_ERROR
        assert result != ExitCode.CRYPTO_ERROR


# ---------------------------------------------------------------------------
# TC-CLI-12 ~ TC-CLI-20: vault unlock
# ---------------------------------------------------------------------------

class TestCmdUnlock:
    """cmd_unlock 测试组。"""

    def test_unlock_normal(self, tmp_path):
        """TC-CLI-12: 正常解密还原文件。"""
        vault_dir = _setup_keystore(tmp_path)
        original_content = b"secret data here"
        file_path = _create_test_file(tmp_path, content=original_content)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            result = cmd_unlock(vault_path=vault_path, keep=True, vault_dir=vault_dir)
        assert result == ExitCode.SUCCESS
        restored_path = VaultFileIO.resolve_original_path(vault_path)
        assert restored_path.read_bytes() == original_content

    def test_unlock_default_removes_vault(self, tmp_path):
        """TC-CLI-13: 解密后默认删除 .vault 文件。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, vault_dir=vault_dir)
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        assert vault_path.exists()
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            cmd_unlock(vault_path=vault_path, vault_dir=vault_dir)
        assert not vault_path.exists()

    def test_unlock_keep_preserves_vault(self, tmp_path):
        """TC-CLI-14: --keep 保留 .vault 文件。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, vault_dir=vault_dir)
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            cmd_unlock(vault_path=vault_path, keep=True, vault_dir=vault_dir)
        assert vault_path.exists()

    def test_unlock_keystore_not_initialized(self, tmp_path):
        """TC-CLI-15: 密钥库未初始化返回退出码 4。"""
        vault_dir = tmp_path / ".vault"
        vault_path = tmp_path / "test.vault"
        vault_path.write_bytes(b"\x00" * 40)
        result = cmd_unlock(vault_path=vault_path, vault_dir=vault_dir)
        assert result == ExitCode.KEYSTORE_NOT_INITIALIZED

    def test_unlock_file_not_found(self, tmp_path):
        """TC-CLI-16: 文件不存在返回退出码 2。"""
        vault_dir = _setup_keystore(tmp_path)
        missing = tmp_path / "nonexistent.vault"
        result = cmd_unlock(vault_path=missing, vault_dir=vault_dir)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_unlock_non_vault_suffix(self, tmp_path):
        """TC-CLI-17: 非 .vault 后缀返回退出码 2。"""
        vault_dir = _setup_keystore(tmp_path)
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("data", encoding="utf-8")
        result = cmd_unlock(vault_path=txt_file, vault_dir=vault_dir)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_unlock_directory_path(self, tmp_path):
        """TC-CLI-18: 路径为目录返回退出码 2。"""
        vault_dir = _setup_keystore(tmp_path)
        subdir = tmp_path / "dir.vault"
        subdir.mkdir()
        result = cmd_unlock(vault_path=subdir, vault_dir=vault_dir)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_unlock_wrong_password(self, tmp_path):
        """TC-CLI-19: 口令错误返回退出码 3。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["correctpw1", "correctpw1"]):
            cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        with patch("vault_cli.cli.password.getpass.getpass", return_value="wrongpassword"):
            result = cmd_unlock(vault_path=vault_path, keep=True, vault_dir=vault_dir)
        assert result == ExitCode.CRYPTO_ERROR

    def test_unlock_invalid_vault_format(self, tmp_path):
        """TC-CLI-20: 文件格式无效返回退出码 3。"""
        vault_dir = _setup_keystore(tmp_path)
        vault_path = tmp_path / "bad.vault"
        vault_path.write_bytes(b"\x00" * 10)  # 过小
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            result = cmd_unlock(vault_path=vault_path, keep=True, vault_dir=vault_dir)
        assert result == ExitCode.CRYPTO_ERROR

    def test_unlock_vault_delete_failure_returns_general_error(self, tmp_path):
        """TC-CLI-27: .vault 文件删除失败返回退出码 1（GENERAL_ERROR）而非 3（CRYPTO_ERROR）。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path)
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        with patch("vault_cli.cli.password.getpass.getpass", return_value="testpassword"):
            with patch("vault_cli.cli.commands.unlock.VaultFileIO.remove_original", side_effect=OSError("Permission denied")):
                result = cmd_unlock(vault_path=vault_path, vault_dir=vault_dir)
        assert result == ExitCode.GENERAL_ERROR
        assert result != ExitCode.CRYPTO_ERROR


# ---------------------------------------------------------------------------
# TC-CLI-21 ~ TC-CLI-25: vault list
# ---------------------------------------------------------------------------

class TestCmdList:
    """cmd_list 测试组。"""

    def test_list_with_vault_files(self, tmp_path):
        """TC-CLI-21: 有加密文件返回 SUCCESS。"""
        vault_dir = _setup_keystore(tmp_path)
        file_path = _create_test_file(tmp_path, "a.txt", b"data")
        with patch("vault_cli.cli.password.getpass.getpass", side_effect=["testpassword", "testpassword"]):
            cmd_lock(file_path=file_path, keep=True, vault_dir=vault_dir)
        result = cmd_list(directory=tmp_path)
        assert result == ExitCode.SUCCESS

    def test_list_no_vault_files(self, tmp_path):
        """TC-CLI-22: 无加密文件返回 SUCCESS。"""
        result = cmd_list(directory=tmp_path)
        assert result == ExitCode.SUCCESS

    def test_list_directory_not_found(self, tmp_path):
        """TC-CLI-23: 目录不存在返回退出码 2。"""
        missing = tmp_path / "nonexistent"
        result = cmd_list(directory=missing)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_list_path_is_file(self, tmp_path):
        """TC-CLI-24: 路径非目录返回退出码 2。"""
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        result = cmd_list(directory=f)
        assert result == ExitCode.ARGUMENT_ERROR

    def test_list_default_directory(self, tmp_path):
        """TC-CLI-25: 默认目录（Path.cwd()）。"""
        result = cmd_list()
        assert result == ExitCode.SUCCESS
