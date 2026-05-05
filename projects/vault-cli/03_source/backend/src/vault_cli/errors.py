"""vault-cli 统一异常定义。

异常体系：
    VaultError (基类)
      |-- KeystoreNotInitializedError
      |-- KeystoreAlreadyInitializedError
      |-- AuthenticationError
      |-- VaultFileFormatError
      |-- VaultFileNotFoundError
      |-- PasswordTooShortError
      |-- PasswordMismatchError
      |-- InvalidFileError
"""


class VaultError(Exception):
    """vault-cli 异常基类。"""


class KeystoreNotInitializedError(VaultError):
    """密钥库未初始化。"""


class KeystoreAlreadyInitializedError(VaultError):
    """密钥库已存在。"""


class AuthenticationError(VaultError):
    """认证标签校验失败（口令错误或文件篡改）。"""


class VaultFileFormatError(VaultError):
    """ .vault 文件格式无效。"""


class VaultFileNotFoundError(VaultError):
    """文件不存在。"""


class PasswordTooShortError(VaultError):
    """口令长度不足。"""

    def __init__(self, min_length: int = 8, actual_length: int = 0) -> None:
        self.min_length = min_length
        self.actual_length = actual_length
        super().__init__(
            f"口令长度不足：至少需要 {min_length} 个字符，实际 {actual_length} 个字符"
        )


class PasswordMismatchError(VaultError):
    """两次口令不一致。"""


class InvalidFileError(VaultError):
    """文件类型无效（如 unlock 非 .vault 文件、路径为目录等）。"""
