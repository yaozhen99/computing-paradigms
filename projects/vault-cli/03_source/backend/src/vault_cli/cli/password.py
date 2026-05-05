"""口令安全输入：封装 getpass，处理口令输入/确认/重试逻辑。"""

from __future__ import annotations

import getpass

from vault_cli.errors import PasswordMismatchError, PasswordTooShortError

# 常量
MIN_PASSWORD_LENGTH = 8
MAX_CONFIRM_RETRIES = 3


class PasswordReader:
    """口令安全输入封装。

    使用 getpass 实现不可回显的口令输入，处理确认和重试逻辑。
    口令以 bytes 形式返回，不在本类中持久化。
    """

    @staticmethod
    def read_and_confirm() -> bytes:
        """读取口令并确认（用于 lock 命令）。

        要求两次输入一致，最多重试 MAX_CONFIRM_RETRIES 次。
        口令长度至少 MIN_PASSWORD_LENGTH 个字符。

        Returns:
            bytes: 口令的字节形式

        Raises:
            PasswordTooShortError: 口令长度不足
            PasswordMismatchError: 超过最大重试次数仍不匹配
        """
        for attempt in range(MAX_CONFIRM_RETRIES):
            password = getpass.getpass("输入口令: ")
            if len(password) < MIN_PASSWORD_LENGTH:
                raise PasswordTooShortError(
                    min_length=MIN_PASSWORD_LENGTH,
                    actual_length=len(password),
                )

            confirm = getpass.getpass("确认口令: ")
            if password == confirm:
                return password.encode("utf-8")

            remaining = MAX_CONFIRM_RETRIES - attempt - 1
            if remaining > 0:
                print(f"口令不一致，请重新输入（剩余 {remaining} 次机会）")

        raise PasswordMismatchError(
            f"口令确认失败，已超过 {MAX_CONFIRM_RETRIES} 次重试上限"
        )

    @staticmethod
    def read() -> bytes:
        """读取口令（用于 unlock 命令，单次输入）。

        Returns:
            bytes: 口令的字节形式
        """
        password = getpass.getpass("输入口令: ")
        return password.encode("utf-8")
