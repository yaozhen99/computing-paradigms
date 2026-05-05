"""vault list 子命令处理。"""

from __future__ import annotations

from pathlib import Path

from vault_cli.cli.exit_codes import ExitCode
from vault_cli.errors import InvalidFileError
from vault_cli.fileio.vault_io import VaultFileIO


def cmd_list(directory: Path | None = None) -> ExitCode:
    """处理 vault list 子命令。

    扫描目录下的 .vault 文件并列出。

    Args:
        directory: 扫描目录路径，默认当前工作目录

    Returns:
        ExitCode: 退出码
    """
    if directory is None:
        directory = Path.cwd()

    # 检查目录有效性
    if not directory.exists():
        print(f"错误：目录不存在：{directory}")
        return ExitCode.ARGUMENT_ERROR
    if not directory.is_dir():
        print(f"错误：指定路径不是目录：{directory}")
        return ExitCode.ARGUMENT_ERROR

    try:
        vault_files = VaultFileIO.scan_vault_files(directory)
    except InvalidFileError as exc:
        print(f"错误：{exc}")
        return ExitCode.ARGUMENT_ERROR

    if not vault_files:
        print(f"当前目录下没有加密文件 ({directory})")
        return ExitCode.SUCCESS

    print(f"找到 {len(vault_files)} 个加密文件 ({directory}):")
    print()
    for info in vault_files:
        size_str = _format_size(info.size)
        time_str = (
            info.encrypted_at.strftime("%Y-%m-%d %H:%M:%S")
            if info.encrypted_at
            else "不可用"
        )
        print(f"  {info.filename:<40s} {size_str:>10s}  {time_str}")

    return ExitCode.SUCCESS


def _format_size(size: int) -> str:
    """格式化文件大小。

    Args:
        size: 文件大小（字节）

    Returns:
        str: 格式化后的大小字符串
    """
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"
