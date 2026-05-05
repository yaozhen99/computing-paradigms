"""vault lock 子命令处理。"""

from __future__ import annotations

from pathlib import Path

from vault_cli.cli.exit_codes import ExitCode
from vault_cli.cli.password import PasswordReader
from vault_cli.crypto.service import CryptoService
from vault_cli.errors import (
    InvalidFileError,
    KeystoreNotInitializedError,
    PasswordMismatchError,
    PasswordTooShortError,
    VaultFileNotFoundError,
)
from vault_cli.fileio.vault_io import VaultFileIO
from vault_cli.keymgr.manager import KeyManager


def cmd_lock(
    file_path: Path,
    keep: bool = False,
    vault_dir: Path | None = None,
) -> ExitCode:
    """处理 vault lock <file> 子命令。

    加密指定文件，生成 .vault 文件。

    Args:
        file_path: 待加密文件路径
        keep: 是否保留原文件，默认 False（删除原文件）
        vault_dir: 密钥库目录路径，默认 ~/.vault/

    Returns:
        ExitCode: 退出码
    """
    if vault_dir is None:
        vault_dir = Path.home() / ".vault"

    # 检查密钥库是否已初始化
    if not KeyManager.is_initialized(vault_dir):
        print("错误：密钥库未初始化，请先执行 vault init")
        return ExitCode.KEYSTORE_NOT_INITIALIZED

    # 检查文件有效性
    if not file_path.exists():
        print(f"错误：文件不存在：{file_path}")
        return ExitCode.ARGUMENT_ERROR
    if file_path.is_dir():
        print(f"错误：路径为目录，不是文件：{file_path}")
        return ExitCode.ARGUMENT_ERROR

    # 读取口令
    try:
        password = PasswordReader.read_and_confirm()
    except PasswordTooShortError as exc:
        print(f"错误：{exc}")
        return ExitCode.GENERAL_ERROR
    except PasswordMismatchError as exc:
        print(f"错误：{exc}")
        return ExitCode.GENERAL_ERROR

    # 派生密钥
    salt = KeyManager.load_salt(vault_dir)
    key = KeyManager.derive_key(password, salt)

    try:
        # 读取原文件
        plaintext = VaultFileIO.read_original(file_path)
        original_size = len(plaintext)

        # 加密
        encrypted = CryptoService.encrypt(plaintext, key)

        # 写入 .vault 文件
        vault_path = VaultFileIO.resolve_vault_path(file_path)
        VaultFileIO.write_vault(vault_path, encrypted)
        vault_size = vault_path.stat().st_size

    except VaultFileNotFoundError as exc:
        print(f"错误：{exc}")
        return ExitCode.ARGUMENT_ERROR
    except InvalidFileError as exc:
        print(f"错误：{exc}")
        return ExitCode.ARGUMENT_ERROR
    except Exception as exc:
        print(f"加密失败：{exc}")
        return ExitCode.CRYPTO_ERROR

    # 删除原文件（除非指定 --keep），独立于加密 try 块
    original_removed = False
    if not keep:
        try:
            VaultFileIO.remove_original(file_path)
            original_removed = True
        except OSError as exc:
            print(f"错误：原文件删除失败：{exc}")
            return ExitCode.GENERAL_ERROR

    print(f"文件已加密：{file_path} -> {vault_path}")
    if not keep:
        print(f"原文件已删除：{file_path}")
    return ExitCode.SUCCESS
