"""vault init 子命令处理。"""

from __future__ import annotations

from pathlib import Path

from vault_cli.cli.exit_codes import ExitCode
from vault_cli.errors import KeystoreAlreadyInitializedError
from vault_cli.keymgr.manager import KeyManager


def cmd_init(vault_dir: Path | None = None) -> ExitCode:
    """处理 vault init 子命令。

    初始化密钥库（创建 .vault 目录、生成盐值、写入配置）。

    Args:
        vault_dir: 密钥库目录路径，默认 ~/.vault/

    Returns:
        ExitCode: 退出码
    """
    if vault_dir is None:
        vault_dir = Path.home() / ".vault"

    if KeyManager.is_initialized(vault_dir):
        print(f"密钥库已存在，无需重复初始化 ({vault_dir})")
        return ExitCode.SUCCESS

    try:
        config = KeyManager.init_keystore(vault_dir)
    except KeystoreAlreadyInitializedError:
        print(f"密钥库已存在，无需重复初始化 ({vault_dir})")
        return ExitCode.SUCCESS
    except OSError as exc:
        print(f"密钥库初始化失败：{exc}")
        return ExitCode.GENERAL_ERROR

    print(f"密钥库已初始化于 {vault_dir}")
    print(f"  盐值长度：{config.salt_length} 字节")
    print(f"  加密算法：{config.algorithm}")
    print(f"  KDF：{config.kdf}")
    print(f"  迭代次数：{config.iterations:,}")
    return ExitCode.SUCCESS
