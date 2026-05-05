"""VaultFileIO 文件 I/O 层测试。

对应用例: TC-FI-01 ~ TC-FI-18
"""

import os
import struct

import pytest

from vault_cli.crypto.service import EncryptedData
from vault_cli.fileio.vault_io import VaultFileIO, VaultFileInfo, VAULT_VERSION, HEADER_BYTES
from vault_cli.errors import (
    InvalidFileError,
    VaultFileFormatError,
    VaultFileNotFoundError,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _make_encrypted_data(ciphertext=b"cipher", iv=None, auth_tag=None):
    """构造 EncryptedData 用于测试。"""
    return EncryptedData(
        iv=iv or os.urandom(12),
        auth_tag=auth_tag or os.urandom(16),
        ciphertext=ciphertext,
    )


def _write_raw_vault(filepath, version=VAULT_VERSION, iv=None, auth_tag=None, ciphertext=b""):
    """直接写入原始 .vault 文件（绕过 VaultFileIO 用于格式测试）。"""
    iv = iv or os.urandom(12)
    auth_tag = auth_tag or os.urandom(16)
    with open(filepath, "wb") as f:
        f.write(struct.pack(">I", version))
        f.write(iv)
        f.write(auth_tag)
        f.write(ciphertext)


# ---------------------------------------------------------------------------
# TC-FI-01 ~ TC-FI-02: write_vault / read_vault 一致性
# ---------------------------------------------------------------------------

class TestVaultFileIOWriteRead:
    """VaultFileIO write_vault / read_vault 测试组。"""

    def test_write_vault_creates_file_correct_size(self, tmp_path):
        """TC-FI-01: 正常写入，文件大小正确。"""
        data = _make_encrypted_data(ciphertext=b"hello")
        filepath = tmp_path / "test.vault"
        VaultFileIO.write_vault(filepath, data)
        expected_size = 4 + 12 + 16 + len(data.ciphertext)
        assert filepath.stat().st_size == expected_size

    def test_write_then_read_consistency(self, tmp_path):
        """TC-FI-02: 写入后读取一致性。"""
        data = _make_encrypted_data(ciphertext=b"consistency_test")
        filepath = tmp_path / "test.vault"
        VaultFileIO.write_vault(filepath, data)
        result = VaultFileIO.read_vault(filepath)
        assert result.iv == data.iv
        assert result.auth_tag == data.auth_tag
        assert result.ciphertext == data.ciphertext


# ---------------------------------------------------------------------------
# TC-FI-03 ~ TC-FI-06: read_vault 异常
# ---------------------------------------------------------------------------

class TestVaultFileIOReadVault:
    """VaultFileIO.read_vault 异常测试组。"""

    def test_read_nonexistent_file_raises_not_found(self, tmp_path):
        """TC-FI-03: 文件不存在。"""
        with pytest.raises(VaultFileNotFoundError):
            VaultFileIO.read_vault(tmp_path / "no.vault")

    def test_read_file_too_small_raises_format_error(self, tmp_path):
        """TC-FI-04: 文件过小。"""
        small_file = tmp_path / "tiny.vault"
        small_file.write_bytes(b"\x00" * 16)
        with pytest.raises(VaultFileFormatError, match="文件过小"):
            VaultFileIO.read_vault(small_file)

    def test_read_wrong_version_raises_format_error(self, tmp_path):
        """TC-FI-05: 版本号错误。"""
        filepath = tmp_path / "badver.vault"
        _write_raw_vault(filepath, version=0x00000002)
        with pytest.raises(VaultFileFormatError, match="不支持的版本号"):
            VaultFileIO.read_vault(filepath)

    def test_read_minimum_valid_file(self, tmp_path):
        """TC-FI-06: 最小合法文件（仅头部 32 字节，密文为空）。"""
        filepath = tmp_path / "min.vault"
        _write_raw_vault(filepath, ciphertext=b"")
        result = VaultFileIO.read_vault(filepath)
        assert result.ciphertext == b""


# ---------------------------------------------------------------------------
# TC-FI-07 ~ TC-FI-12: 原文件操作
# ---------------------------------------------------------------------------

class TestVaultFileIOOriginalFile:
    """VaultFileIO 原文件操作测试组。"""

    def test_read_original_normal(self, tmp_path):
        """TC-FI-07: 读取正常文件。"""
        f = tmp_path / "hello.txt"
        f.write_text("hello", encoding="utf-8")
        content = VaultFileIO.read_original(f)
        assert content == b"hello"

    def test_read_original_nonexistent_raises_not_found(self, tmp_path):
        """TC-FI-08: 读取不存在的文件。"""
        with pytest.raises(VaultFileNotFoundError):
            VaultFileIO.read_original(tmp_path / "nope.txt")

    def test_read_original_directory_raises_invalid_file(self, tmp_path):
        """TC-FI-09: 读取目录。"""
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(InvalidFileError):
            VaultFileIO.read_original(d)

    def test_write_original_content_matches(self, tmp_path):
        """TC-FI-10: 写入原文件内容一致。"""
        f = tmp_path / "out.txt"
        VaultFileIO.write_original(f, b"data123")
        assert f.read_bytes() == b"data123"

    def test_remove_original_deletes_file(self, tmp_path):
        """TC-FI-11: 删除原文件。"""
        f = tmp_path / "del.txt"
        f.write_text("bye", encoding="utf-8")
        VaultFileIO.remove_original(f)
        assert not f.exists()

    def test_remove_original_nonexistent_raises_not_found(self, tmp_path):
        """TC-FI-12: 删除不存在的文件。"""
        with pytest.raises(VaultFileNotFoundError):
            VaultFileIO.remove_original(tmp_path / "ghost.txt")


# ---------------------------------------------------------------------------
# TC-FI-13 ~ TC-FI-15: 路径解析
# ---------------------------------------------------------------------------

class TestVaultFileIOPathResolution:
    """VaultFileIO 路径解析测试组。"""

    def test_resolve_vault_path(self):
        """TC-FI-13: resolve_vault_path。"""
        from pathlib import Path
        assert VaultFileIO.resolve_vault_path(Path("secret.txt")) == Path("secret.txt.vault")

    def test_resolve_original_path_with_vault_suffix(self):
        """TC-FI-14: resolve_original_path - .vault 后缀。"""
        from pathlib import Path
        assert VaultFileIO.resolve_original_path(Path("secret.txt.vault")) == Path("secret.txt")

    def test_resolve_original_path_without_vault_suffix(self):
        """TC-FI-15: resolve_original_path - 无 .vault 后缀原样返回。"""
        from pathlib import Path
        assert VaultFileIO.resolve_original_path(Path("readme.md")) == Path("readme.md")


# ---------------------------------------------------------------------------
# TC-FI-16 ~ TC-FI-18: 目录扫描
# ---------------------------------------------------------------------------

class TestVaultFileIOScan:
    """VaultFileIO.scan_vault_files 测试组。"""

    def test_scan_with_vault_files(self, tmp_path):
        """TC-FI-16: 有 .vault 文件。"""
        (tmp_path / "a.vault").write_bytes(b"\x00" * 40)
        (tmp_path / "b.vault").write_bytes(b"\x00" * 50)
        (tmp_path / "c.txt").write_text("plain", encoding="utf-8")
        results = VaultFileIO.scan_vault_files(tmp_path)
        assert len(results) == 2
        assert results[0].filename == "a.vault"
        assert results[1].filename == "b.vault"
        assert all(isinstance(r, VaultFileInfo) for r in results)

    def test_scan_no_vault_files(self, tmp_path):
        """TC-FI-17: 无 .vault 文件。"""
        (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
        results = VaultFileIO.scan_vault_files(tmp_path)
        assert results == []

    def test_scan_non_directory_raises_invalid_file(self, tmp_path):
        """TC-FI-18: 非目录路径。"""
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        with pytest.raises(InvalidFileError):
            VaultFileIO.scan_vault_files(f)
