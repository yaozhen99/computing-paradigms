"""退出码定义。

退出码分段定义，便于脚本集成：
    0 = 成功
    1 = 一般错误
    2 = 参数错误
    3 = 加密/解密错误
    4 = 密钥库未初始化
"""

from enum import IntEnum


class ExitCode(IntEnum):
    """统一退出码常量。"""

    SUCCESS = 0
    GENERAL_ERROR = 1
    ARGUMENT_ERROR = 2
    CRYPTO_ERROR = 3
    KEYSTORE_NOT_INITIALIZED = 4
