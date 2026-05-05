# vault-cli 测试需求

**创建时间**：2026-05-03 23:30
**被测模块**：vault-cli 全模块（crypto、keymgr、fileio、cli）
**对应需求**：`02_design/api_contracts.md`

## 1. 测试范围

- **包含**：
  - 加密服务层（`vault_cli.crypto.service`）：AES-256-GCM 加密/解密、IV 生成、认证标签校验、密钥长度校验
  - 密钥管理层（`vault_cli.keymgr.manager`）：PBKDF2-SHA256 密钥派生、盐值管理、密钥库初始化/检测、安全权限设置
  - 文件 I/O 层（`vault_cli.fileio.vault_io`）：.vault 文件读写序列化、原文件读写、文件删除、路径解析、目录扫描
  - 口令输入层（`vault_cli.cli.password`）：口令读取/确认/重试、长度校验
  - CLI 命令层（`vault_cli.cli.commands`）：init/lock/unlock/list 子命令的参数校验、错误处理、退出码返回
  - CLI 入口（`vault_cli.cli.main`）：参数解析、命令分发、无命令时帮助输出
  - 错误体系（`vault_cli.errors`）：各异常类的定义与属性
  - 退出码（`vault_cli.cli.exit_codes`）：ExitCode 枚举值正确性

- **不包含**：
  - 性能/压力测试（v1 范围外）
  - 跨平台权限测试（Windows NTFS 权限为默认行为，不做深度验证）
  - GUI/交互式终端渲染测试
  - 打包/安装流程测试（pyproject.toml 构建流程）

## 2. 测试目标

- **功能完整性**：所有 API 契约中定义的子命令（init/lock/unlock/list）在正常流和异常流下均能正确执行，返回符合契约的退出码
- **加密往返验证**：加密后解密能完整还原原始明文，数据零损失
- **安全校验**：口令错误时 AES-GCM 认证标签校验必须失败，返回 `AuthenticationError`；文件篡改同样触发认证失败
- **口令策略执行**：口令长度不足 8 字符时拒绝操作；两次输入不一致时在 3 次重试后拒绝
- **密钥库状态管理**：未初始化时 lock/unlock 返回退出码 4；已初始化时 init 返回成功（幂等）
- **文件格式健壮性**：.vault 文件过小、版本号错误、后缀不符等情况均有明确错误返回
- **路径解析正确性**：lock 生成 .vault 后缀文件路径；unlock 正确去除 .vault 后缀还原原始路径

## 3. 测试策略概述

- **单元测试**：对 crypto、keymgr、fileio、password 各模块的核心方法进行独立测试，使用 Mock 隔离外部依赖
- **集成测试**：测试 CLI 命令层到各底层模块的串联，验证退出码和输出消息
- **端到端往返测试**：从 init -> lock -> unlock 完整流程验证，确保加密解密数据一致
- **所有测试使用 pytest 框架**，通过 `tmp_path` fixture 创建临时目录，不依赖外部环境

## 4. 测试环境要求

- **硬件/系统**：Windows 11 / Linux / macOS 均可（跨平台兼容）
- **软件依赖**：
  - Python >= 3.11
  - pytest >= 7.0
  - cryptography >= 41.0
- **测试数据**：
  - 使用 `os.urandom()` 生成随机明文数据
  - 使用 `tmp_path` fixture 创建临时目录和文件
  - 口令 Mock 数据：有效口令（>=8 字符）、短口令、不匹配口令
  - 文件 Mock 数据：正常文件、空文件、大文件（边界测试用）

## 5. 风险与重点

- **高风险区域**：
  - **加密/解密往返**：核心安全功能，任何不一致均为严重缺陷
  - **认证标签校验**：口令错误必须触发 `AuthenticationError`，否则为安全漏洞
  - **口令输入 Mock**：`getpass` 为终端交互，测试中必须 Mock 替换
  - **密钥库状态检查**：lock/unlock 对未初始化密钥库的拒绝是安全关键路径
  - **原子写入**：.vault 文件写入使用临时文件+重命名，需验证异常时临时文件被清理
- **中风险区域**：
  - 退出码映射准确性（异常类型到退出码的对应关系）
  - 文件路径解析（相对路径、绝对路径、带空格路径）
  - .vault 文件格式校验（过小、版本号错误）
