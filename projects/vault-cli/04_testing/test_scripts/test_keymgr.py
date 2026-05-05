"""KeyManager 密钥管理层测试。

对应用例: TC-KM-01 ~ TC-KM-14
"""

import json
import os

import pytest

from vault_cli.keymgr.manager import KeyManager, KeystoreConfig, SALT_LENGTH, KEY_LENGTH, KDF_ITERATIONS
from vault_cli.errors import KeystoreAlreadyInitializedError, KeystoreNotInitializedError


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _init_keystore(vault_dir):
    """快捷初始化密钥库。"""
    return KeyManager.init_keystore(vault_dir)


# ---------------------------------------------------------------------------
# TC-KM-01 ~ TC-KM-04: init_keystore
# ---------------------------------------------------------------------------

class TestKeyManagerInitKeystore:
    """KeyManager.init_keystore 测试组。"""

    def test_first_init_creates_files(self, tmp_path):
        """TC-KM-01: 首次初始化，创建 salt.bin 和 config.json。"""
        vault_dir = tmp_path / ".vault"
        config = _init_keystore(vault_dir)
        assert isinstance(config, KeystoreConfig)
        assert (vault_dir / "salt.bin").is_file()
        assert (vault_dir / "config.json").is_file()

    def test_duplicate_init_raises_error(self, tmp_path):
        """TC-KM-02: 重复初始化抛出 KeystoreAlreadyInitializedError。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        with pytest.raises(KeystoreAlreadyInitializedError):
            KeyManager.init_keystore(vault_dir)

    def test_config_json_content(self, tmp_path):
        """TC-KM-03: config.json 内容校验。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        with open(vault_dir / "config.json", encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["version"] == 1
        assert cfg["algorithm"] == "AES-256-GCM"
        assert cfg["kdf"] == "PBKDF2-SHA256"
        assert cfg["iterations"] == KDF_ITERATIONS
        assert cfg["salt_length"] == SALT_LENGTH
        assert cfg["key_length"] == KEY_LENGTH

    def test_salt_bin_length(self, tmp_path):
        """TC-KM-04: salt.bin 长度校验。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        salt = (vault_dir / "salt.bin").read_bytes()
        assert len(salt) == SALT_LENGTH


# ---------------------------------------------------------------------------
# TC-KM-05 ~ TC-KM-08: is_initialized
# ---------------------------------------------------------------------------

class TestKeyManagerIsInitialized:
    """KeyManager.is_initialized 测试组。"""

    def test_initialized_returns_true(self, tmp_path):
        """TC-KM-05: 已初始化检测。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        assert KeyManager.is_initialized(vault_dir) is True

    def test_not_initialized_returns_false(self, tmp_path):
        """TC-KM-06: 未初始化检测。"""
        vault_dir = tmp_path / ".vault"
        assert KeyManager.is_initialized(vault_dir) is False

    def test_missing_salt_returns_false(self, tmp_path):
        """TC-KM-07: 缺少 salt.bin。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        (vault_dir / "salt.bin").unlink()
        assert KeyManager.is_initialized(vault_dir) is False

    def test_missing_config_returns_false(self, tmp_path):
        """TC-KM-08: 缺少 config.json。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        (vault_dir / "config.json").unlink()
        assert KeyManager.is_initialized(vault_dir) is False


# ---------------------------------------------------------------------------
# TC-KM-09 ~ TC-KM-12: derive_key
# ---------------------------------------------------------------------------

class TestKeyManagerDeriveKey:
    """KeyManager.derive_key 测试组。"""

    def test_derive_key_returns_32_bytes(self):
        """TC-KM-09: 正常派生返回 32 字节密钥。"""
        password = b"test_password"
        salt = os.urandom(SALT_LENGTH)
        key = KeyManager.derive_key(password, salt)
        assert len(key) == KEY_LENGTH

    def test_derive_key_deterministic(self):
        """TC-KM-10: 相同口令+相同盐值，结果一致。"""
        password = b"test_password"
        salt = os.urandom(SALT_LENGTH)
        key1 = KeyManager.derive_key(password, salt)
        key2 = KeyManager.derive_key(password, salt)
        assert key1 == key2

    def test_derive_key_different_password(self):
        """TC-KM-11: 不同口令+相同盐值，结果不同。"""
        salt = os.urandom(SALT_LENGTH)
        key1 = KeyManager.derive_key(b"password_a", salt)
        key2 = KeyManager.derive_key(b"password_b", salt)
        assert key1 != key2

    def test_derive_key_different_salt(self):
        """TC-KM-12: 相同口令+不同盐值，结果不同。"""
        password = b"test_password"
        salt1 = os.urandom(SALT_LENGTH)
        salt2 = os.urandom(SALT_LENGTH)
        key1 = KeyManager.derive_key(password, salt1)
        key2 = KeyManager.derive_key(password, salt2)
        assert key1 != key2


# ---------------------------------------------------------------------------
# TC-KM-13 ~ TC-KM-14: load_salt
# ---------------------------------------------------------------------------

class TestKeyManagerLoadSalt:
    """KeyManager.load_salt 测试组。"""

    def test_load_salt_returns_correct_data(self, tmp_path):
        """TC-KM-13: 正常加载盐值。"""
        vault_dir = tmp_path / ".vault"
        _init_keystore(vault_dir)
        salt = KeyManager.load_salt(vault_dir)
        expected = (vault_dir / "salt.bin").read_bytes()
        assert salt == expected

    def test_load_salt_not_initialized_raises_error(self, tmp_path):
        """TC-KM-14: 未初始化加载盐值抛出异常。"""
        vault_dir = tmp_path / ".vault"
        with pytest.raises(KeystoreNotInitializedError):
            KeyManager.load_salt(vault_dir)
