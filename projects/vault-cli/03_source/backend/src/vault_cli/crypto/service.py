"""加密服务层：AES-256-GCM 加解密、IV 生成、认证标签校验。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from vault_cli.errors import AuthenticationError

# 常量
KEY_LENGTH = 32  # AES-256 密钥长度（字节）
IV_LENGTH = 12  # AES-GCM 推荐 IV 长度（字节）
TAG_LENGTH = 16  # AES-GCM 认证标签长度（字节）


@dataclass(frozen=True)
class EncryptedData:
    """加密结果数据结构。

    Attributes:
        iv: 初始化向量（12 字节）
        auth_tag: 认证标签（16 字节）
        ciphertext: 加密后的密文
    """

    iv: bytes
    auth_tag: bytes
    ciphertext: bytes


class CryptoService:
    """AES-256-GCM 加密/解密服务。

    无状态类，不存储密钥或 IV，由调用方在每次操作时传入密钥。
    """

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> EncryptedData:
        """使用 AES-256-GCM 加密数据。

        Args:
            plaintext: 待加密的明文数据
            key: 加密密钥（必须为 32 字节）

        Returns:
            EncryptedData: 包含 iv、auth_tag、ciphertext 的加密结果

        Raises:
            ValueError: 密钥长度不为 32 字节
        """
        if len(key) != KEY_LENGTH:
            raise ValueError(
                f"密钥长度必须为 {KEY_LENGTH} 字节，实际 {len(key)} 字节"
            )
        iv = os.urandom(IV_LENGTH)
        aesgcm = AESGCM(key)
        # AESGCM.encrypt 返回 ciphertext + auth_tag 拼接
        ct_with_tag = aesgcm.encrypt(iv, plaintext, None)
        ciphertext = ct_with_tag[:-TAG_LENGTH]
        auth_tag = ct_with_tag[-TAG_LENGTH:]
        return EncryptedData(iv=iv, auth_tag=auth_tag, ciphertext=ciphertext)

    @staticmethod
    def decrypt(encrypted: EncryptedData, key: bytes) -> bytes:
        """使用 AES-256-GCM 解密数据。

        Args:
            encrypted: 包含 iv、auth_tag、ciphertext 的加密数据
            key: 解密密钥（必须为 32 字节）

        Returns:
            bytes: 解密后的明文数据

        Raises:
            ValueError: 密钥长度不为 32 字节
            AuthenticationError: 认证标签校验失败（口令错误或文件篡改）
        """
        if len(key) != KEY_LENGTH:
            raise ValueError(
                f"密钥长度必须为 {KEY_LENGTH} 字节，实际 {len(key)} 字节"
            )
        aesgcm = AESGCM(key)
        # AESGCM.decrypt 需要 ciphertext + auth_tag 拼接形式
        ct_with_tag = encrypted.ciphertext + encrypted.auth_tag
        try:
            plaintext = aesgcm.decrypt(encrypted.iv, ct_with_tag, None)
        except Exception as exc:
            raise AuthenticationError(
                "认证标签校验失败：口令错误或文件已被篡改"
            ) from exc
        return plaintext
