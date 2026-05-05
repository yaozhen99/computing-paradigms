"""文件 I/O 层：.vault 文件读写与序列化、原文件处理、权限控制。"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from vault_cli.crypto.service import EncryptedData
from vault_cli.errors import (
    InvalidFileError,
    VaultFileFormatError,
    VaultFileNotFoundError,
)

# .vault 文件格式常量
VAULT_VERSION = 0x00000001  # 版本号 v1
VERSION_BYTES = 4
IV_BYTES = 12
TAG_BYTES = 16
HEADER_BYTES = VERSION_BYTES + IV_BYTES + TAG_BYTES  # 32 字节


@dataclass(frozen=True)
class VaultFileInfo:
    """ .vault 文件元信息。

    Attributes:
        filename: .vault 文件名
        size: 文件大小（字节）
        encrypted_at: 加密时间（若元数据中包含），None 表示不可用
    """

    filename: str
    size: int
    encrypted_at: datetime | None


class VaultFileIO:
    """ .vault 文件读写核心类。"""

    @staticmethod
    def write_vault(filepath: Path, data: EncryptedData) -> None:
        """将加密数据序列化写入 .vault 文件。

        采用临时文件 + 原子重命名，防止写入中断导致数据损坏。

        Args:
            filepath: .vault 文件路径
            data: 加密数据（iv, auth_tag, ciphertext）
        """
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        try:
            with open(tmp_path, "wb") as f:
                # 版本号 uint32 big-endian
                f.write(struct.pack(">I", VAULT_VERSION))
                # IV (12 字节)
                f.write(data.iv)
                # Auth Tag (16 字节)
                f.write(data.auth_tag)
                # 密文（变长）
                f.write(data.ciphertext)
            # 原子重命名
            os.replace(tmp_path, filepath)
        except Exception:
            # 清理临时文件
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    @staticmethod
    def read_vault(filepath: Path) -> EncryptedData:
        """从 .vault 文件反序列化读取加密数据。

        Args:
            filepath: .vault 文件路径

        Returns:
            EncryptedData: 加密数据

        Raises:
            VaultFileNotFoundError: 文件不存在
            VaultFileFormatError: 文件格式无效
        """
        if not filepath.is_file():
            raise VaultFileNotFoundError(f"文件不存在：{filepath}")

        file_size = filepath.stat().st_size
        if file_size < HEADER_BYTES:
            raise VaultFileFormatError(
                f"文件格式无效：文件过小（{file_size} 字节），"
                f"至少需要 {HEADER_BYTES} 字节"
            )

        with open(filepath, "rb") as f:
            raw = f.read()

        version = struct.unpack(">I", raw[:VERSION_BYTES])[0]
        if version != VAULT_VERSION:
            raise VaultFileFormatError(
                f"不支持的版本号：0x{version:08X}，"
                f"期望 0x{VAULT_VERSION:08X}"
            )

        iv = raw[VERSION_BYTES : VERSION_BYTES + IV_BYTES]
        auth_tag = raw[VERSION_BYTES + IV_BYTES : HEADER_BYTES]
        ciphertext = raw[HEADER_BYTES:]

        return EncryptedData(iv=iv, auth_tag=auth_tag, ciphertext=ciphertext)

    @staticmethod
    def read_original(filepath: Path) -> bytes:
        """读取原文件内容。

        Args:
            filepath: 原文件路径

        Returns:
            bytes: 文件内容

        Raises:
            VaultFileNotFoundError: 文件不存在
            InvalidFileError: 文件路径为目录或符号链接
        """
        if not filepath.exists():
            raise VaultFileNotFoundError(f"文件不存在：{filepath}")
        if filepath.is_dir():
            raise InvalidFileError(f"路径为目录，不是文件：{filepath}")
        if filepath.is_symlink():
            raise InvalidFileError(f"路径为符号链接，不支持：{filepath}")
        return filepath.read_bytes()

    @staticmethod
    def write_original(filepath: Path, plaintext: bytes) -> None:
        """将解密后的明文写入原文件。

        采用临时文件 + 原子重命名。

        Args:
            filepath: 原文件路径
            plaintext: 解密后的明文数据
        """
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        try:
            tmp_path.write_bytes(plaintext)
            os.replace(tmp_path, filepath)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    @staticmethod
    def remove_original(filepath: Path) -> None:
        """安全删除原文件。

        使用 os.remove()，不做多次覆写（v1 简化）。

        Args:
            filepath: 待删除文件路径

        Raises:
            VaultFileNotFoundError: 文件不存在
        """
        if not filepath.exists():
            raise VaultFileNotFoundError(f"文件不存在：{filepath}")
        os.remove(filepath)

    @staticmethod
    def resolve_vault_path(filepath: Path) -> Path:
        """计算对应的 .vault 文件路径。

        Args:
            filepath: 原文件路径

        Returns:
            Path: 对应的 .vault 文件路径
        """
        return Path(str(filepath) + ".vault")

    @staticmethod
    def resolve_original_path(vault_path: Path) -> Path:
        """从 .vault 路径还原原始文件路径。

        Args:
            vault_path: .vault 文件路径

        Returns:
            Path: 原始文件路径
        """
        path_str = str(vault_path)
        if path_str.endswith(".vault"):
            return Path(path_str[: -len(".vault")])
        return vault_path

    @staticmethod
    def scan_vault_files(directory: Path) -> list[VaultFileInfo]:
        """扫描目录下的 .vault 文件。

        Args:
            directory: 扫描目录路径

        Returns:
            list[VaultFileInfo]: .vault 文件元信息列表

        Raises:
            InvalidFileError: 指定路径不是目录
        """
        if not directory.is_dir():
            raise InvalidFileError(f"指定路径不是目录：{directory}")

        results: list[VaultFileInfo] = []
        for item in directory.iterdir():
            if item.is_file() and item.suffix == ".vault":
                stat = item.stat()
                results.append(
                    VaultFileInfo(
                        filename=item.name,
                        size=stat.st_size,
                        encrypted_at=datetime.fromtimestamp(stat.st_mtime),
                    )
                )
        return sorted(results, key=lambda x: x.filename)

    @staticmethod
    def set_secure_permissions(filepath: Path) -> None:
        """设置文件安全权限（Linux: 600）。

        Args:
            filepath: 文件路径
        """
        if os.name != "nt":
            os.chmod(filepath, 0o600)
