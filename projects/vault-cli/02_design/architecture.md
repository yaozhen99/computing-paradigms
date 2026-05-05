# vault-cli 系统分层架构设计

**版本**：v1.0
**创建时间**：2026-05-03 23:05
**架构师**：architect
**关联需求**：`01_requirements/prd_final.md`

---

## 1. 架构总览

vault-cli 是一个纯 CLI 离线文件加密工具，无网络层，采用四层分层架构。各层之间通过明确的函数调用接口通信，数据向下传递，错误向上冒泡。

```
+----------------------------------------------------------+
|                    命令分发层 (CLI Layer)                  |
|         argparse 子命令路由 | 口令安全输入 | 退出码管理     |
+----------------------------------------------------------+
                              |
                              v
+----------------------------------------------------------+
|                   加密服务层 (Crypto Layer)                |
|         AES-256-GCM 加解密 | IV 生成 | 认证标签校验        |
+----------------------------------------------------------+
                              |
                              v
+----------------------------------------------------------+
|                   密钥管理层 (KeyMgr Layer)                |
|     PBKDF2-SHA256 口令派生 | 盐值生成/读取 | 密钥库初始化   |
+----------------------------------------------------------+
                              |
                              v
+----------------------------------------------------------+
|                   文件 I/O 层 (FileIO Layer)               |
|    .vault 文件读写/序列化 | 原文件处理 | 权限控制           |
+----------------------------------------------------------+
```

---

## 2. 各层职责

### 2.1 命令分发层 (CLI Layer)

**职责**：CLI 入口、子命令路由、用户交互、退出码管理

| 组件 | 职责 |
|:---|:---|
| `main()` | argparse 顶层解析，分发到子命令处理函数 |
| `cmd_init()` | 处理 `vault init` 子命令 |
| `cmd_lock()` | 处理 `vault lock <file>` 子命令 |
| `cmd_unlock()` | 处理 `vault unlock <file.vault>` 子命令 |
| `cmd_list()` | 处理 `vault list` 子命令 |
| `PasswordReader` | 封装 getpass，处理口令输入/确认/重试逻辑 |
| `ExitCode` (enum) | 统一退出码常量定义 |

**设计约束**：
- 命令分发层不包含任何加密逻辑，仅做参数校验和结果输出
- 口令通过 `PasswordReader` 读取后，以 `bytes` 形式向下传递，不在命令层存储
- 退出码：0=成功，1=一般错误，2=参数错误，3=加密/解密错误，4=密钥库未初始化

### 2.2 加密服务层 (Crypto Layer)

**职责**：AES-256-GCM 加解密、IV 生成、认证标签校验

| 组件 | 职责 |
|:---|:---|
| `CryptoService` | 加密/解密的核心服务类 |
| `encrypt(plaintext: bytes, key: bytes) -> EncryptedData` | 加密方法，返回结构化加密结果 |
| `decrypt(encrypted: EncryptedData, key: bytes) -> bytes` | 解密方法，校验认证标签 |
| `EncryptedData` (dataclass) | 封装 iv + auth_tag + ciphertext 的数据结构 |

**设计约束**：
- IV 由 `os.urandom(12)` 生成，每次加密必须使用新 IV
- AES-256-GCM 的 key 长度必须为 32 字节（256 位）
- 认证标签校验失败时抛出 `AuthenticationError`，不产生任何输出
- `CryptoService` 为无状态类，不存储密钥或 IV

### 2.3 密钥管理层 (KeyMgr Layer)

**职责**：PBKDF2-SHA256 口令派生、盐值管理、密钥库初始化

| 组件 | 职责 |
|:---|:---|
| `KeyManager` | 密钥派生与密钥库管理的核心类 |
| `init_keystore(vault_dir: Path) -> None` | 初始化密钥库（创建 .vault 目录、生成盐值、写入配置） |
| `derive_key(password: bytes, salt: bytes) -> bytes` | PBKDF2-SHA256 派生 256 位密钥 |
| `load_salt(vault_dir: Path) -> bytes` | 从密钥库加载盐值 |
| `is_initialized(vault_dir: Path) -> bool` | 检查密钥库是否已初始化 |
| `KeystoreConfig` (dataclass) | 配置数据结构（算法、迭代次数等） |

**设计约束**：
- PBKDF2-SHA256 迭代次数：600,000（OWASP 2023 推荐）
- 盐值长度：16 字节（128 位），由 `os.urandom(16)` 生成
- 密钥库目录默认路径：`~/.vault/`（用户主目录下）
- 配置文件为 JSON 格式：`~/.vault/config.json`
- 盐值文件为二进制格式：`~/.vault/salt.bin`
- 密钥不在内存中持久化，用完即丢弃

### 2.4 文件 I/O 层 (FileIO Layer)

**职责**：.vault 文件读写与序列化、原文件处理、权限控制

| 组件 | 职责 |
|:---|:---|
| `VaultFileIO` | .vault 文件读写核心类 |
| `write_vault(filepath: Path, data: EncryptedData) -> None` | 将加密数据序列化写入 .vault 文件 |
| `read_vault(filepath: Path) -> EncryptedData` | 从 .vault 文件反序列化读取加密数据 |
| `remove_original(filepath: Path) -> None` | 安全删除原文件 |
| `resolve_vault_path(filepath: Path) -> Path` | 计算对应的 .vault 文件路径 |
| `resolve_original_path(vault_path: Path) -> Path` | 从 .vault 路径还原原始文件路径 |
| `scan_vault_files(directory: Path) -> list[VaultFileInfo]` | 扫描目录下的 .vault 文件 |
| `VaultFileInfo` (dataclass) | .vault 文件元信息（文件名、大小、加密时间） |
| `set_secure_permissions(filepath: Path) -> None` | 设置文件安全权限（Linux: 600） |

**设计约束**：
- .vault 文件二进制格式：`[版本号 4B][IV 12B][Auth Tag 16B][密文 变长]`
- 版本号：`0x00000001`（uint32 big-endian）
- 写入时先写临时文件，再原子重命名（防止写入中断导致数据损坏）
- 原文件删除使用 `os.remove()`，不做多次覆写（v1 简化）
- 文件路径校验：必须为常规文件，不能是目录或符号链接

---

## 3. 层间交互流程

### 3.1 vault init 流程

```
cmd_init()
  |
  +-> KeyManager.is_initialized(vault_dir)
  |     |-- 已初始化 -> 输出提示，退出码 0
  |
  +-> KeyManager.init_keystore(vault_dir)
        |-- 生成盐值 (16 bytes)
        |-- 写入 salt.bin
        |-- 写入 config.json
        |-- 设置权限 (Linux: 600)
  |
  +-> 输出成功信息，退出码 0
```

### 3.2 vault lock 流程

```
cmd_lock(file_path)
  |
  +-> KeyManager.is_initialized(vault_dir)
  |     |-- 未初始化 -> 输出错误，退出码 4
  |
  +-> PasswordReader.read_and_confirm()
  |     |-- 超过3次不匹配 -> 退出码 1
  |     |-- 长度不足8字符 -> 提示拒绝，退出码 1
  |
  +-> KeyManager.load_salt(vault_dir)
  +-> KeyManager.derive_key(password, salt)
  |
  +-> VaultFileIO.read_original(file_path)
  |
  +-> CryptoService.encrypt(plaintext, key)
  |     |-- 生成 IV (12 bytes)
  |     |-- AES-256-GCM 加密
  |     |-- 返回 EncryptedData(iv, auth_tag, ciphertext)
  |
  +-> VaultFileIO.write_vault(vault_path, encrypted_data)
  |
  +-> [若无 --keep] VaultFileIO.remove_original(file_path)
  |
  +-> 输出成功信息，退出码 0
```

### 3.3 vault unlock 流程

```
cmd_unlock(vault_path)
  |
  +-> KeyManager.is_initialized(vault_dir)
  |     |-- 未初始化 -> 输出错误，退出码 4
  |
  +-> 校验文件后缀为 .vault，否则退出码 2
  |
  +-> PasswordReader.read() (单次输入)
  |
  +-> KeyManager.load_salt(vault_dir)
  +-> KeyManager.derive_key(password, salt)
  |
  +-> VaultFileIO.read_vault(vault_path)
  |
  +-> CryptoService.decrypt(encrypted_data, key)
  |     |-- 认证标签校验失败 -> 抛出 AuthenticationError
  |     |-- 捕获后输出错误信息，退出码 3
  |
  +-> VaultFileIO.write_original(original_path, plaintext)
  |
  +-> [若无 --keep] VaultFileIO.remove_original(vault_path)
  |
  +-> 输出成功信息，退出码 0
```

### 3.4 vault list 流程

```
cmd_list()
  |
  +-> VaultFileIO.scan_vault_files(cwd)
  |     |-- 无 .vault 文件 -> 输出友好提示，退出码 0
  |
  +-> 格式化输出文件列表（文件名、大小、加密时间）
  |
  +-> 退出码 0
```

---

## 4. 目录结构设计

```
vault-cli/
  src/
    vault_cli/
      __init__.py
      cli/
        __init__.py
        main.py            # argparse 入口与子命令路由
        commands/
          __init__.py
          init.py           # cmd_init()
          lock.py           # cmd_lock()
          unlock.py         # cmd_unlock()
          list.py           # cmd_list()
        password.py         # PasswordReader
        exit_codes.py       # ExitCode enum
      crypto/
        __init__.py
        service.py          # CryptoService, EncryptedData
      keymgr/
        __init__.py
        manager.py          # KeyManager, KeystoreConfig
      fileio/
        __init__.py
        vault_io.py         # VaultFileIO, VaultFileInfo
      errors.py             # 统一异常定义
  tests/
    test_crypto/
    test_keymgr/
    test_fileio/
    test_cli/
  pyproject.toml
```

---

## 5. 异常体系

```
VaultError (基类)
  |-- KeystoreNotInitializedError   # 密钥库未初始化
  |-- KeystoreAlreadyInitializedError  # 密钥库已存在
  |-- AuthenticationError           # 认证标签校验失败（口令错误或文件篡改）
  |-- VaultFileFormatError          # .vault 文件格式无效
  |-- VaultFileNotFoundError        # 文件不存在
  |-- PasswordTooShortError         # 口令长度不足
  |-- PasswordMismatchError         # 两次口令不一致
  |-- InvalidFileError              # 文件类型无效（如 unlock 非 .vault 文件）
```

---

## 6. 关键设计决策

| 决策编号 | 决策 | 理由 |
|:---|:---|:---|
| D-01 | 密钥库位于用户主目录 `~/.vault/` | 跨项目共享密钥库，避免每个工作目录都有独立盐值 |
| D-02 | 盐值与配置文件分离存储 | 盐值为二进制，配置为 JSON，职责清晰 |
| D-03 | .vault 文件采用二进制格式而非 Base64 | 避免编码开销，文件更紧凑，直接映射到加密输出结构 |
| D-04 | 加密服务为无状态设计 | 密钥不存储在服务中，由调用方在每次操作时传入，降低泄露风险 |
| D-05 | 写入采用临时文件+原子重命名 | 防止写入中断导致数据损坏，保证 .vault 文件要么完整要么不存在 |
| D-06 | 口令不在内存中持久化 | 派生密钥后立即清除口令引用，减少内存驻留时间 |
| D-07 | 退出码分段定义 | 0=成功，1=一般错误，2=参数错误，3=加密错误，4=密钥库未初始化，便于脚本集成 |
