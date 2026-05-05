"""密钥管理层：PBKDF2-SHA256 口令派生、盐值管理、密钥库初始化。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from vault_cli.errors import (
    KeystoreAlreadyInitializedError,
    KeystoreNotInitializedError,
)

# 常量
SALT_LENGTH = 16  # 盐值长度（字节）
KEY_LENGTH = 32  # 派生密钥长度（字节）
KDF_ITERATIONS = 600_000  # PBKDF2 迭代次数（OWASP 2023 推荐）
IV_LENGTH = 12
TAG_LENGTH = 16
CONFIG_VERSION = 1


@dataclass(frozen=True)
class KeystoreConfig:
    """密钥库配置数据结构。

    Attributes:
        version: 配置格式版本
        algorithm: 加密算法名称
        kdf: 密钥派生函数名称
        iterations: KDF 迭代次数
        salt_length: 盐值长度（字节）
        key_length: 密钥长度（字节）
        iv_length: IV 长度（字节）
        tag_length: 认证标签长度（字节）
    """

    version: int = CONFIG_VERSION
    algorithm: str = "AES-256-GCM"
    kdf: str = "PBKDF2-SHA256"
    iterations: int = KDF_ITERATIONS
    salt_length: int = SALT_LENGTH
    key_length: int = KEY_LENGTH
    iv_length: int = IV_LENGTH
    tag_length: int = TAG_LENGTH

    def to_dict(self) -> dict:
        """转换为字典，用于 JSON 序列化。"""
        return {
            "version": self.version,
            "algorithm": self.algorithm,
            "kdf": self.kdf,
            "iterations": self.iterations,
            "salt_length": self.salt_length,
            "key_length": self.key_length,
            "iv_length": self.iv_length,
            "tag_length": self.tag_length,
        }


class KeyManager:
    """密钥派生与密钥库管理的核心类。"""

    @staticmethod
    def is_initialized(vault_dir: Path) -> bool:
        """检查密钥库是否已初始化。

        Args:
            vault_dir: 密钥库目录路径

        Returns:
            bool: 密钥库是否已初始化
        """
        config_path = vault_dir / "config.json"
        salt_path = vault_dir / "salt.bin"
        return config_path.is_file() and salt_path.is_file()

    @staticmethod
    def init_keystore(vault_dir: Path) -> KeystoreConfig:
        """初始化密钥库。

        创建 .vault 目录、生成盐值、写入配置。

        Args:
            vault_dir: 密钥库目录路径

        Returns:
            KeystoreConfig: 密钥库配置

        Raises:
            KeystoreAlreadyInitializedError: 密钥库已存在
        """
        if KeyManager.is_initialized(vault_dir):
            raise KeystoreAlreadyInitializedError("密钥库已存在，无需重复初始化")

        vault_dir.mkdir(parents=True, exist_ok=True)

        # 生成盐值并写入
        salt = os.urandom(SALT_LENGTH)
        salt_path = vault_dir / "salt.bin"
        salt_path.write_bytes(salt)

        # 写入配置
        config = KeystoreConfig()
        config_path = vault_dir / "config.json"
        config_path.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 设置文件安全权限（Linux: 600）
        KeyManager._set_secure_permissions(salt_path)
        KeyManager._set_secure_permissions(config_path)

        return config

    @staticmethod
    def derive_key(password: bytes, salt: bytes) -> bytes:
        """使用 PBKDF2-SHA256 从口令派生密钥。

        Args:
            password: 口令（字节形式）
            salt: 盐值

        Returns:
            bytes: 派生的 256 位密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        return kdf.derive(password)

    @staticmethod
    def load_salt(vault_dir: Path) -> bytes:
        """从密钥库加载盐值。

        Args:
            vault_dir: 密钥库目录路径

        Returns:
            bytes: 盐值

        Raises:
            KeystoreNotInitializedError: 密钥库未初始化
        """
        if not KeyManager.is_initialized(vault_dir):
            raise KeystoreNotInitializedError(
                "密钥库未初始化，请先执行 vault init"
            )
        salt_path = vault_dir / "salt.bin"
        return salt_path.read_bytes()

    @staticmethod
    def _set_secure_permissions(filepath: Path) -> None:
        """设置文件安全权限。

        Linux: 600（仅当前用户可读写）
        Windows: 依赖 NTFS 默认权限

        Args:
            filepath: 文件路径
        """
        if os.name != "nt":
            os.chmod(filepath, 0o600)
