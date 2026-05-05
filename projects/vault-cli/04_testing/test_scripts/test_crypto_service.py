"""CryptoService 加密服务层测试。

对应用例: TC-CR-01 ~ TC-CR-15
"""

import os

import pytest

from vault_cli.crypto.service import CryptoService, EncryptedData, KEY_LENGTH, IV_LENGTH, TAG_LENGTH
from vault_cli.errors import AuthenticationError


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _make_key(length: int = KEY_LENGTH) -> bytes:
    """生成指定长度的随机密钥。"""
    return os.urandom(length)


# ---------------------------------------------------------------------------
# TC-CR-01 ~ TC-CR-07: encrypt
# ---------------------------------------------------------------------------

class TestCryptoServiceEncrypt:
    """CryptoService.encrypt 测试组。"""

    def test_encrypt_nonempty_plaintext_returns_valid_structure(self):
        """TC-CR-01: 正常加密-非空明文，返回结构字段合法。"""
        key = _make_key()
        result = CryptoService.encrypt(b"hello", key)
        assert isinstance(result, EncryptedData)
        assert len(result.iv) == IV_LENGTH
        assert len(result.auth_tag) == TAG_LENGTH
        assert len(result.ciphertext) > 0

    def test_encrypt_empty_plaintext_returns_valid_structure(self):
        """TC-CR-02: 正常加密-空明文。"""
        key = _make_key()
        result = CryptoService.encrypt(b"", key)
        assert isinstance(result, EncryptedData)
        assert len(result.iv) == IV_LENGTH
        assert len(result.auth_tag) == TAG_LENGTH

    def test_encrypt_large_plaintext(self):
        """TC-CR-03: 正常加密-大文件明文（1MB）。"""
        key = _make_key()
        big_data = os.urandom(1024 * 1024)
        result = CryptoService.encrypt(big_data, key)
        assert len(result.ciphertext) == len(big_data)

    def test_encrypt_key_too_short_raises_value_error(self):
        """TC-CR-04: 密钥长度错误-过短。"""
        with pytest.raises(ValueError, match="32"):
            CryptoService.encrypt(b"test", os.urandom(16))

    def test_encrypt_key_too_long_raises_value_error(self):
        """TC-CR-05: 密钥长度错误-过长。"""
        with pytest.raises(ValueError, match="32"):
            CryptoService.encrypt(b"test", os.urandom(64))

    def test_encrypt_iv_randomness(self):
        """TC-CR-06: IV 随机性，两次加密的 iv 不同。"""
        key = _make_key()
        r1 = CryptoService.encrypt(b"same", key)
        r2 = CryptoService.encrypt(b"same", key)
        assert r1.iv != r2.iv

    def test_encrypt_ciphertext_randomness(self):
        """TC-CR-07: 密文随机性，两次加密的 ciphertext 不同。"""
        key = _make_key()
        r1 = CryptoService.encrypt(b"same", key)
        r2 = CryptoService.encrypt(b"same", key)
        assert r1.ciphertext != r2.ciphertext


# ---------------------------------------------------------------------------
# TC-CR-08 ~ TC-CR-15: decrypt
# ---------------------------------------------------------------------------

class TestCryptoServiceDecrypt:
    """CryptoService.decrypt 测试组。"""

    def test_decrypt_restores_nonempty_plaintext(self):
        """TC-CR-08: 正常解密-还原非空明文。"""
        key = _make_key()
        original = b"hello world"
        encrypted = CryptoService.encrypt(original, key)
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == original

    def test_decrypt_restores_empty_plaintext(self):
        """TC-CR-09: 加密解密往返-空明文。"""
        key = _make_key()
        encrypted = CryptoService.encrypt(b"", key)
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == b""

    def test_decrypt_restores_large_plaintext(self):
        """TC-CR-10: 加密解密往返-大文件（1MB）。"""
        key = _make_key()
        big_data = os.urandom(1024 * 1024)
        encrypted = CryptoService.encrypt(big_data, key)
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == big_data

    def test_decrypt_wrong_key_raises_authentication_error(self):
        """TC-CR-11: 口令错误-认证标签失败。"""
        key_a = _make_key()
        key_b = _make_key()
        encrypted = CryptoService.encrypt(b"secret", key_a)
        with pytest.raises(AuthenticationError):
            CryptoService.decrypt(encrypted, key_b)

    def test_decrypt_tampered_ciphertext_raises_authentication_error(self):
        """TC-CR-12: 密文篡改-认证失败。"""
        key = _make_key()
        encrypted = CryptoService.encrypt(b"secret", key)
        tampered_ct = bytearray(encrypted.ciphertext)
        if len(tampered_ct) > 0:
            tampered_ct[0] ^= 0xFF
        else:
            tampered_ct = b"\x00"
        tampered = EncryptedData(iv=encrypted.iv, auth_tag=encrypted.auth_tag, ciphertext=bytes(tampered_ct))
        with pytest.raises(AuthenticationError):
            CryptoService.decrypt(tampered, key)

    def test_decrypt_tampered_auth_tag_raises_authentication_error(self):
        """TC-CR-13: Auth Tag 篡改-认证失败。"""
        key = _make_key()
        encrypted = CryptoService.encrypt(b"secret", key)
        tampered_tag = bytearray(encrypted.auth_tag)
        tampered_tag[0] ^= 0xFF
        tampered = EncryptedData(iv=encrypted.iv, auth_tag=bytes(tampered_tag), ciphertext=encrypted.ciphertext)
        with pytest.raises(AuthenticationError):
            CryptoService.decrypt(tampered, key)

    def test_decrypt_tampered_iv_raises_authentication_error(self):
        """TC-CR-14: IV 篡改-认证失败。"""
        key = _make_key()
        encrypted = CryptoService.encrypt(b"secret", key)
        tampered_iv = bytearray(encrypted.iv)
        tampered_iv[0] ^= 0xFF
        tampered = EncryptedData(iv=bytes(tampered_iv), auth_tag=encrypted.auth_tag, ciphertext=encrypted.ciphertext)
        with pytest.raises(AuthenticationError):
            CryptoService.decrypt(tampered, key)

    def test_decrypt_key_length_error_raises_value_error(self):
        """TC-CR-15: 密钥长度错误-解密。"""
        key = _make_key()
        encrypted = CryptoService.encrypt(b"test", key)
        with pytest.raises(ValueError, match="32"):
            CryptoService.decrypt(encrypted, os.urandom(16))
