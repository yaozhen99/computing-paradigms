"""vault unlock 子命令处理。"""

from __future__ import annotations

from pathlib import Path

from vault_cli.cli.exit_codes import ExitCode
from vault_cli.cli.password import PasswordReader
from vault_cli.crypto.service import CryptoService
from vault_cli.errors import (
    AuthenticationError,
    InvalidFileError,
    KeystoreNotInitializedError,
    VaultFileFormatError,
    VaultFileNotFoundError,
)
from vault_cli.fileio.vault_io import VaultFileIO
from vault_cli.keymgr.manager import KeyManager


def cmd_unlock(
    vault_path: Path,
    keep: bool = False,
    vault_dir: Path | None = None,
) -> ExitCode:
    """处理 vault unlock <file.vault> 子命令。

    解密指定 .vault 文件，还原原始文件。

    Args:
        vault_path: 待解密的 .vault 文件路径
        keep: 是否保留 .vault 文件，默认 False（删除 .vault 文件）
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

    # 校验文件后缀为 .vault
    if vault_path.suffix != ".vault":
        print(f"错误：文件后缀必须为 .vault：{vault_path}")
        return ExitCode.ARGUMENT_ERROR

    # 检查文件有效性
    if not vault_path.exists():
        print(f"错误：文件不存在：{vault_path}")
        return ExitCode.ARGUMENT_ERROR
    if vault_path.is_dir():
        print(f"错误：路径为目录，不是文件：{vault_path}")
        return ExitCode.ARGUMENT_ERROR

    # 读取口令（单次输入）
    password = PasswordReader.read()

    # 派生密钥
    salt = KeyManager.load_salt(vault_dir)
    key = KeyManager.derive_key(password, salt)

    try:
        # 读取 .vault 文件
        encrypted = VaultFileIO.read_vault(vault_path)

        # 解密
        plaintext = CryptoService.decrypt(encrypted, key)
        restored_size = len(plaintext)

        # 写入原文件
        original_path = VaultFileIO.resolve_original_path(vault_path)
        VaultFileIO.write_original(original_path, plaintext)

    except AuthenticationError as exc:
        print(f"错误：{exc}")
        return ExitCode.CRYPTO_ERROR
    except VaultFileFormatError as exc:
        print(f"错误：文件格式无效：{exc}")
        return ExitCode.CRYPTO_ERROR
    except VaultFileNotFoundError as exc:
        print(f"错误：{exc}")
        return ExitCode.ARGUMENT_ERROR
    except InvalidFileError as exc:
        print(f"错误：{exc}")
        return ExitCode.ARGUMENT_ERROR
    except Exception as exc:
        print(f"解密失败：{exc}")
        return ExitCode.CRYPTO_ERROR

    # 删除 .vault 文件（除非指定 --keep），独立于解密 try 块
    vault_removed = False
    if not keep:
        try:
            VaultFileIO.remove_original(vault_path)
            vault_removed = True
        except OSError as exc:
            print(f"错误：加密文件删除失败：{exc}")
            return ExitCode.GENERAL_ERROR

    print(f"文件已解密：{vault_path} -> {original_path}")
    if not keep:
        print(f"加密文件已删除：{vault_path}")
    return ExitCode.SUCCESS
