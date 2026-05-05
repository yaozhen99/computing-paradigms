# vault-cli 后端开发笔记

**创建时间**：2026-05-03 23:20
**对应计划**：02_design/architecture.md, 02_design/api_contracts.md

## 1. 本次开发目标

实现 vault-cli 后端完整代码树，包含以下模块：
- CLI 入口与子命令路由（vault init/lock/unlock/list）
- 加密服务层（AES-256-GCM）
- 密钥管理层（PBKDF2-SHA256 口令派生、盐值存储）
- 文件 I/O 层（.vault 文件读写、原子写入）
- 口令安全输入（不可回显）
- 错误处理与退出码

## 2. 实施方案概要

1. **目录结构**：严格按照 architecture.md 第4节定义的目录规范，源码置于 `03_source/backend/src/vault_cli/` 下
2. **加密算法**：AES-256-GCM，IV 由 os.urandom(12) 生成，Key 长度 32 字节
3. **密钥派生**：PBKDF2-SHA256，迭代 600,000 次，盐值 16 字节
4. **文件格式**：.vault 二进制格式 = [版本号4B][IV12B][AuthTag16B][密文变长]
5. **原子写入**：先写 .tmp 临时文件，再 os.replace 原子重命名
6. **口令输入**：getpass 封装，lock 需确认（最多3次），unlock 单次输入
7. **退出码**：0=成功, 1=一般错误, 2=参数错误, 3=加密错误, 4=密钥库未初始化
8. **异常体系**：VaultError 基类，派生 8 个具体异常类

## 3. 涉及文件清单（预期）

- `03_source/backend/src/vault_cli/__init__.py` — 包初始化
- `03_source/backend/src/vault_cli/errors.py` — 统一异常定义
- `03_source/backend/src/vault_cli/cli/__init__.py` — CLI 包初始化
- `03_source/backend/src/vault_cli/cli/main.py` — argparse 入口与子命令路由
- `03_source/backend/src/vault_cli/cli/commands/__init__.py` — 命令包初始化
- `03_source/backend/src/vault_cli/cli/commands/init.py` — cmd_init()
- `03_source/backend/src/vault_cli/cli/commands/lock.py` — cmd_lock()
- `03_source/backend/src/vault_cli/cli/commands/unlock.py` — cmd_unlock()
- `03_source/backend/src/vault_cli/cli/commands/list.py` — cmd_list()
- `03_source/backend/src/vault_cli/cli/password.py` — PasswordReader
- `03_source/backend/src/vault_cli/cli/exit_codes.py` — ExitCode enum
- `03_source/backend/src/vault_cli/crypto/__init__.py` — Crypto 包初始化
- `03_source/backend/src/vault_cli/crypto/service.py` — CryptoService, EncryptedData
- `03_source/backend/src/vault_cli/keymgr/__init__.py` — KeyMgr 包初始化
- `03_source/backend/src/vault_cli/keymgr/manager.py` — KeyManager, KeystoreConfig
- `03_source/backend/src/vault_cli/fileio/__init__.py` — FileIO 包初始化
- `03_source/backend/src/vault_cli/fileio/vault_io.py` — VaultFileIO, VaultFileInfo
- `03_source/backend/pyproject.toml` — 项目配置

## 4. 注意事项

- 密钥不在内存中持久化，用完即丢弃
- 认证标签校验失败时抛出 AuthenticationError，不产生任何输出
- .vault 写入必须原子重命名
- 原文件删除不做多次覆写（v1 简化）
- 文件路径校验：必须为常规文件，不能是目录或符号链接
- Windows 下 NTFS 权限不做特殊处理

## 5. 待确认问题

- [x] 目录规范确认：按 architecture.md 第4节，源码在 src/vault_cli/ 下，但项目约定放在 03_source/backend/ 下
- [x] 密钥库路径：默认 ~/.vault/，跨项目共享
