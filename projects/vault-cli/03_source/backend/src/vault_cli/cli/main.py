"""CLI 入口：argparse 顶层解析，分发到子命令处理函数。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vault_cli import __version__
from vault_cli.cli.commands.init import cmd_init
from vault_cli.cli.commands.list import cmd_list
from vault_cli.cli.commands.lock import cmd_lock
from vault_cli.cli.commands.unlock import cmd_unlock
from vault_cli.cli.exit_codes import ExitCode


def build_parser() -> argparse.ArgumentParser:
    """构建 argparse 解析器。

    Returns:
        argparse.ArgumentParser: 配置好的解析器
    """
    parser = argparse.ArgumentParser(
        prog="vault",
        description="vault-cli: 纯 CLI 离线文件加密工具",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    # vault init
    init_parser = subparsers.add_parser(
        "init",
        help="初始化密钥库",
    )
    init_parser.add_argument(
        "--vault-dir",
        type=Path,
        default=None,
        help="密钥库目录路径（默认 ~/.vault/）",
    )

    # vault lock
    lock_parser = subparsers.add_parser(
        "lock",
        help="加密文件",
    )
    lock_parser.add_argument(
        "file",
        type=Path,
        help="待加密文件路径",
    )
    lock_parser.add_argument(
        "--keep",
        action="store_true",
        default=False,
        help="保留原文件（默认删除原文件）",
    )
    lock_parser.add_argument(
        "--vault-dir",
        type=Path,
        default=None,
        help="密钥库目录路径（默认 ~/.vault/）",
    )

    # vault unlock
    unlock_parser = subparsers.add_parser(
        "unlock",
        help="解密文件",
    )
    unlock_parser.add_argument(
        "file",
        type=Path,
        help="待解密的 .vault 文件路径",
    )
    unlock_parser.add_argument(
        "--keep",
        action="store_true",
        default=False,
        help="保留 .vault 文件（默认删除 .vault 文件）",
    )
    unlock_parser.add_argument(
        "--vault-dir",
        type=Path,
        default=None,
        help="密钥库目录路径（默认 ~/.vault/）",
    )

    # vault list
    list_parser = subparsers.add_parser(
        "list",
        help="列出加密文件",
    )
    list_parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="扫描目录路径（默认当前工作目录）",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口函数。

    Args:
        argv: 命令行参数，默认使用 sys.argv[1:]

    Returns:
        int: 退出码
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return ExitCode.ARGUMENT_ERROR

    if args.command == "init":
        return cmd_init(vault_dir=args.vault_dir)
    elif args.command == "lock":
        return cmd_lock(
            file_path=args.file,
            keep=args.keep,
            vault_dir=args.vault_dir,
        )
    elif args.command == "unlock":
        return cmd_unlock(
            vault_path=args.file,
            keep=args.keep,
            vault_dir=args.vault_dir,
        )
    elif args.command == "list":
        return cmd_list(directory=args.dir)

    # 不应到达此处
    parser.print_help()
    return ExitCode.ARGUMENT_ERROR


def entry_point() -> None:
    """控制台入口点，供 pyproject.toml scripts 使用。"""
    sys.exit(main())
