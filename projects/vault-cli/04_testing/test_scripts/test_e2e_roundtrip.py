"""端到端往返测试。

对应用例: TC-E2E-01 ~ TC-E2E-05
验证完整的 init -> lock -> unlock 流程。
"""

import os
from unittest.mock import patch

import pytest

from vault_cli.cli.commands.init import cmd_init
from vault_cli.cli.commands.lock import cmd_lock
from vault_cli.cli.commands.unlock import cmd_unlock
from vault_cli.cli.exit_codes import ExitCode
from vault_cli.fileio.vault_io import VaultFileIO


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _full_roundtrip(tmp_path, filename, content, password="testpassword", keep=False):
    """执行完整的 init -> lock -> unlock 流程，返回还原内容。"""
    vault_dir = tmp_path / ".vault"
    assert cmd_init(vault_dir=vault_dir) == ExitCode.SUCCESS

    # 创建文件并加密
    file_path = tmp_path / filename
    if isinstance(content, str):
        file_path.write_text(content, encoding="utf-8")
    else:
        file_path.write_bytes(content)

    with patch("vault_cli.cli.password.getpass.getpass", side_effect=[password, password]):
        result = cmd_lock(file_path=file_path, keep=keep, vault_dir=vault_dir)
    assert result == ExitCode.SUCCESS

    vault_path = VaultFileIO.resolve_vault_path(file_path)

    # 解密
    with patch("vault_cli.cli.password.getpass.getpass", return_value=password):
        result = cmd_unlock(vault_path=vault_path, keep=keep, vault_dir=vault_dir)
    assert result == ExitCode.SUCCESS

    # 读取还原的文件
    original_path = VaultFileIO.resolve_original_path(vault_path)
    return original_path.read_bytes()


# ---------------------------------------------------------------------------
# TC-E2E-01 ~ TC-E2E-05
# ---------------------------------------------------------------------------

class TestEndToEndRoundtrip:
    """端到端往返测试组。"""

    def test_full_roundtrip_normal_text(self, tmp_path):
        """TC-E2E-01: 完整流程 init->lock->unlock，还原内容一致。"""
        original = b"hello world"
        restored = _full_roundtrip(tmp_path, "secret.txt", original)
        assert restored == original

    def test_multiple_files_roundtrip(self, tmp_path):
        """TC-E2E-02: 多文件加解密。"""
        vault_dir = tmp_path / ".vault"
        cmd_init(vault_dir=vault_dir)

        files = {
            "file1.txt": b"content one",
            "file2.txt": b"content two",
            "file3.txt": b"content three",
        }
        password = "testpassword"

        for name, content in files.items():
            f = tmp_path / name
            f.write_bytes(content)
            with patch("vault_cli.cli.password.getpass.getpass", side_effect=[password, password]):
                cmd_lock(file_path=f, keep=True, vault_dir=vault_dir)

        for name, content in files.items():
            vault_path = tmp_path / (name + ".vault")
            with patch("vault_cli.cli.password.getpass.getpass", return_value=password):
                cmd_unlock(vault_path=vault_path, keep=True, vault_dir=vault_dir)
            original_path = tmp_path / name
            assert original_path.read_bytes() == content

    def test_empty_file_roundtrip(self, tmp_path):
        """TC-E2E-03: 空文件加密解密。"""
        restored = _full_roundtrip(tmp_path, "empty.txt", b"")
        assert restored == b""

    def test_chinese_content_roundtrip(self, tmp_path):
        """TC-E2E-04: 中文内容加解密。"""
        chinese = "你好世界，加密测试"
        original = chinese.encode("utf-8")
        restored = _full_roundtrip(tmp_path, "chinese.txt", original)
        assert restored == original

    def test_binary_content_roundtrip(self, tmp_path):
        """TC-E2E-05: 二进制文件加解密。"""
        binary_data = os.urandom(4096)
        restored = _full_roundtrip(tmp_path, "binary.dat", binary_data)
        assert restored == binary_data
