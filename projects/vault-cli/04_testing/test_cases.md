# vault-cli 测试用例矩阵

**创建时间**：2026-05-03 23:30
**对应测试需求**：`04_testing/test_req.md`
**对应 API 契约**：`02_design/api_contracts.md`

---

## 1. CryptoService 加密服务层

### 1.1 加密（encrypt）

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CR-01 | 正常加密-非空明文 | 生成 32 字节密钥 | 调用 CryptoService.encrypt(b"hello", key) | 返回 EncryptedData，iv 为 12 字节，auth_tag 为 16 字节，ciphertext 非空 | 高 |
| TC-CR-02 | 正常加密-空明文 | 生成 32 字节密钥 | 调用 CryptoService.encrypt(b"", key) | 返回 EncryptedData，ciphertext 可为空 | 高 |
| TC-CR-03 | 正常加密-大文件明文 | 生成 32 字节密钥，构造 1MB 明文 | 调用 CryptoService.encrypt(big_data, key) | 返回 EncryptedData，ciphertext 长度等于明文长度 | 中 |
| TC-CR-04 | 密钥长度错误-过短 | 构造 16 字节密钥 | 调用 CryptoService.encrypt(b"test", short_key) | 抛出 ValueError，消息包含"32 字节" | 高 |
| TC-CR-05 | 密钥长度错误-过长 | 构造 64 字节密钥 | 调用 CryptoService.encrypt(b"test", long_key) | 抛出 ValueError | 高 |
| TC-CR-06 | IV 随机性 | 生成 32 字节密钥 | 连续两次加密相同明文 | 两次返回的 iv 不同 | 高 |
| TC-CR-07 | 密文随机性 | 生成 32 字节密钥 | 连续两次加密相同明文 | 两次返回的 ciphertext 不同 | 高 |

### 1.2 解密（decrypt）

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CR-08 | 正常解密-还原明文 | 加密 b"hello world" | 用同一密钥解密 | 明文为 b"hello world" | 高 |
| TC-CR-09 | 加密解密往返-空明文 | 加密 b"" | 解密 | 明文为 b"" | 高 |
| TC-CR-10 | 加密解密往返-大文件 | 加密 1MB 随机数据 | 解密 | 明文与原始数据完全一致 | 高 |
| TC-CR-11 | 口令错误-认证标签失败 | 用密钥 A 加密 | 用密钥 B（不同口令派生）解密 | 抛出 AuthenticationError | 高 |
| TC-CR-12 | 密文篡改-认证失败 | 加密数据 | 修改 ciphertext 的一个字节后解密 | 抛出 AuthenticationError | 高 |
| TC-CR-13 | Auth Tag 篡改 | 加密数据 | 修改 auth_tag 的一个字节后解密 | 抛出 AuthenticationError | 高 |
| TC-CR-14 | IV 篡改 | 加密数据 | 修改 iv 的一个字节后解密 | 抛出 AuthenticationError | 高 |
| TC-CR-15 | 密钥长度错误-解密 | 加密数据 | 用 16 字节密钥解密 | 抛出 ValueError | 高 |

---

## 2. KeyManager 密钥管理层

### 2.1 密钥库初始化

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-KM-01 | 首次初始化 | 空临时目录 | 调用 KeyManager.init_keystore(vault_dir) | 创建目录、salt.bin(16字节)、config.json；返回 KeystoreConfig | 高 |
| TC-KM-02 | 重复初始化 | 已初始化的密钥库 | 再次调用 init_keystore | 抛出 KeystoreAlreadyInitializedError | 高 |
| TC-KM-03 | config.json 内容校验 | 首次初始化后 | 读取并解析 config.json | 包含 version=1, algorithm="AES-256-GCM", kdf="PBKDF2-SHA256", iterations=600000 等字段 | 高 |
| TC-KM-04 | salt.bin 长度校验 | 首次初始化后 | 读取 salt.bin | 长度为 16 字节 | 高 |

### 2.2 密钥库状态检测

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-KM-05 | 已初始化检测 | 完整密钥库 | is_initialized(vault_dir) | 返回 True | 高 |
| TC-KM-06 | 未初始化检测 | 空目录 | is_initialized(vault_dir) | 返回 False | 高 |
| TC-KM-07 | 缺少 salt.bin | 删除 salt.bin | is_initialized(vault_dir) | 返回 False | 中 |
| TC-KM-08 | 缺少 config.json | 删除 config.json | is_initialized(vault_dir) | 返回 False | 中 |

### 2.3 密钥派生

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-KM-09 | 正常派生 | 生成口令和盐值 | derive_key(password, salt) | 返回 32 字节密钥 | 高 |
| TC-KM-10 | 确定性验证 | 相同口令+相同盐值 | 两次 derive_key | 结果完全相同 | 高 |
| TC-KM-11 | 不同口令不同密钥 | 不同口令+相同盐值 | 两次 derive_key | 结果不同 | 高 |
| TC-KM-12 | 不同盐值不同密钥 | 相同口令+不同盐值 | 两次 derive_key | 结果不同 | 高 |

### 2.4 盐值加载

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-KM-13 | 正常加载 | 已初始化密钥库 | load_salt(vault_dir) | 返回 16 字节盐值，与 salt.bin 内容一致 | 高 |
| TC-KM-14 | 未初始化加载 | 空目录 | load_salt(vault_dir) | 抛出 KeystoreNotInitializedError | 高 |

---

## 3. VaultFileIO 文件 I/O 层

### 3.1 .vault 文件写入

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-FI-01 | 正常写入 | 构造 EncryptedData | write_vault(filepath, data) | 文件被创建，大小 = 4+12+16+len(ciphertext) | 高 |
| TC-FI-02 | 写入后读取一致性 | 写入后 | read_vault(filepath) | 返回的 iv/auth_tag/ciphertext 与写入一致 | 高 |

### 3.2 .vault 文件读取

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-FI-03 | 文件不存在 | 不存在的路径 | read_vault(path) | 抛出 VaultFileNotFoundError | 高 |
| TC-FI-04 | 文件过小 | 创建 16 字节文件 | read_vault(path) | 抛出 VaultFileFormatError，消息包含"文件过小" | 高 |
| TC-FI-05 | 版本号错误 | 创建文件头版本号=0x00000002 | read_vault(path) | 抛出 VaultFileFormatError，消息包含"不支持的版本号" | 高 |
| TC-FI-06 | 最小合法文件 | 创建仅含 32 字节头部的文件 | read_vault(path) | 成功返回，ciphertext 为空字节 | 中 |

### 3.3 原文件操作

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-FI-07 | 读取正常文件 | 创建文件 hello.txt | read_original(path) | 返回文件内容 | 高 |
| TC-FI-08 | 读取不存在的文件 | 不存在的路径 | read_original(path) | 抛出 VaultFileNotFoundError | 高 |
| TC-FI-09 | 读取目录 | 传入目录路径 | read_original(dir_path) | 抛出 InvalidFileError | 高 |
| TC-FI-10 | 写入原文件 | 构造明文 | write_original(path, data) | 文件内容与 data 一致 | 高 |
| TC-FI-11 | 删除原文件 | 创建文件 | remove_original(path) | 文件不存在 | 高 |
| TC-FI-12 | 删除不存在的文件 | 不存在的路径 | remove_original(path) | 抛出 VaultFileNotFoundError | 高 |

### 3.4 路径解析

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-FI-13 | resolve_vault_path | 传入 secret.txt | resolve_vault_path | 返回 secret.txt.vault | 高 |
| TC-FI-14 | resolve_original_path | 传入 secret.txt.vault | resolve_original_path | 返回 secret.txt | 高 |
| TC-FI-15 | resolve_original_path-无 .vault 后缀 | 传入 readme.md | resolve_original_path | 返回 readme.md（原样返回） | 中 |

### 3.5 目录扫描

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-FI-16 | 有 .vault 文件 | 目录含 a.vault, b.vault, c.txt | scan_vault_files(dir) | 返回 2 个 VaultFileInfo，按文件名排序 | 高 |
| TC-FI-17 | 无 .vault 文件 | 目录仅含普通文件 | scan_vault_files(dir) | 返回空列表 | 高 |
| TC-FI-18 | 非目录路径 | 传入文件路径 | scan_vault_files(file_path) | 抛出 InvalidFileError | 中 |

---

## 4. PasswordReader 口令输入层

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-PW-01 | 正常输入确认 | Mock getpass 返回一致口令（>=8字符） | read_and_confirm() | 返回口令的 bytes 形式 | 高 |
| TC-PW-02 | 口令过短 | Mock getpass 返回 3 字符口令 | read_and_confirm() | 抛出 PasswordTooShortError，min_length=8 | 高 |
| TC-PW-03 | 两次不一致-第1次 | Mock 第1次不匹配，第2次匹配 | read_and_confirm() | 返回口令的 bytes 形式 | 高 |
| TC-PW-04 | 三次不一致 | Mock 三次均不匹配 | read_and_confirm() | 抛出 PasswordMismatchError | 高 |
| TC-PW-05 | 单次读取 | Mock getpass 返回口令 | read() | 返回口令的 bytes 形式 | 高 |
| TC-PW-06 | 空口令读取 | Mock getpass 返回空字符串 | read() | 返回 b"" | 中 |

---

## 5. CLI 子命令层

### 5.1 vault init

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CLI-01 | 首次初始化 | 空临时目录 | cmd_init(vault_dir) | 返回 ExitCode.SUCCESS，目录含 salt.bin 和 config.json | 高 |
| TC-CLI-02 | 重复初始化 | 已初始化密钥库 | cmd_init(vault_dir) | 返回 ExitCode.SUCCESS（幂等），输出"已存在" | 高 |
| TC-CLI-03 | 默认路径初始化 | 不传 vault_dir | cmd_init() | 使用 ~/.vault/，返回 SUCCESS | 中 |

### 5.2 vault lock

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CLI-04 | 正常加密 | 已初始化密钥库，Mock 口令一致 | cmd_lock(file_path, vault_dir) | 返回 SUCCESS，.vault 文件存在 | 高 |
| TC-CLI-05 | 加密后原文件删除（默认） | 不传 --keep | cmd_lock | 原文件不存在，.vault 文件存在 | 高 |
| TC-CLI-06 | 加密后保留原文件（--keep） | keep=True | cmd_lock | 原文件存在，.vault 文件也存在 | 高 |
| TC-CLI-07 | 密钥库未初始化 | 空目录 | cmd_lock(file_path, vault_dir) | 返回 KEYSTORE_NOT_INITIALIZED (4) | 高 |
| TC-CLI-08 | 文件不存在 | 不存在的文件路径 | cmd_lock(missing_file, vault_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-09 | 路径为目录 | 传入目录路径 | cmd_lock(dir_path, vault_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-10 | 口令过短 | Mock getpass 返回短口令 | cmd_lock | 返回 GENERAL_ERROR (1) | 高 |
| TC-CLI-11 | 口令不匹配 | Mock getpass 返回不一致口令×3 | cmd_lock | 返回 GENERAL_ERROR (1) | 高 |
| TC-CLI-26 | 原文件删除失败 | 已初始化密钥库，Mock VaultFileIO.remove_original 抛出 OSError | cmd_lock（不传 --keep） | 返回 GENERAL_ERROR (1)，而非 CRYPTO_ERROR (3) | 高 |

### 5.3 vault unlock

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CLI-12 | 正常解密 | 先 lock 加密文件 | cmd_unlock(vault_path, vault_dir) | 返回 SUCCESS，还原文件内容与原始一致 | 高 |
| TC-CLI-13 | 解密后删除 .vault（默认） | 不传 --keep | cmd_unlock | .vault 文件不存在，原文件存在 | 高 |
| TC-CLI-14 | 解密后保留 .vault（--keep） | keep=True | cmd_unlock | .vault 文件存在，原文件也存在 | 高 |
| TC-CLI-15 | 密钥库未初始化 | 空目录 | cmd_unlock(vault_path, vault_dir) | 返回 KEYSTORE_NOT_INITIALIZED (4) | 高 |
| TC-CLI-16 | 文件不存在 | 不存在的 .vault 文件 | cmd_unlock(missing_path, vault_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-17 | 非 .vault 后缀 | 传入 .txt 文件 | cmd_unlock(txt_path, vault_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-18 | 路径为目录 | 传入目录路径 | cmd_unlock(dir_path, vault_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-19 | 口令错误 | 用不同口令解密 | cmd_unlock | 返回 CRYPTO_ERROR (3) | 高 |
| TC-CLI-20 | 文件格式无效 | 创建损坏的 .vault 文件 | cmd_unlock | 返回 CRYPTO_ERROR (3) | 高 |
| TC-CLI-27 | .vault 文件删除失败 | 先 lock 加密文件，Mock VaultFileIO.remove_original 抛出 OSError | cmd_unlock（不传 --keep） | 返回 GENERAL_ERROR (1)，而非 CRYPTO_ERROR (3) | 高 |

### 5.4 vault list

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-CLI-21 | 有加密文件 | 目录含 .vault 文件 | cmd_list(directory) | 返回 SUCCESS，输出包含文件信息 | 高 |
| TC-CLI-22 | 无加密文件 | 目录无 .vault 文件 | cmd_list(directory) | 返回 SUCCESS，输出"没有加密文件" | 高 |
| TC-CLI-23 | 目录不存在 | 不存在的目录 | cmd_list(missing_dir) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-24 | 路径非目录 | 传入文件路径 | cmd_list(file_path) | 返回 ARGUMENT_ERROR (2) | 高 |
| TC-CLI-25 | 默认目录 | 不传 directory | cmd_list() | 使用 Path.cwd()，返回 SUCCESS | 中 |

---

## 6. 端到端往返测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-E2E-01 | 完整流程 init->lock->unlock | 临时目录 | init -> lock -> unlock | 还原文件内容与原始完全一致 | 高 |
| TC-E2E-02 | 多文件加解密 | 3 个不同文件 | 依次 lock 3 个文件 -> 依次 unlock | 每个文件还原内容一致 | 高 |
| TC-E2E-03 | 空文件加密解密 | 0 字节文件 | lock -> unlock | 还原为空文件 | 高 |
| TC-E2E-04 | 中文内容加解密 | UTF-8 中文文件 | lock -> unlock | 还原内容含中文且一致 | 高 |
| TC-E2E-05 | 二进制文件加解密 | 随机二进制数据 | lock -> unlock | 还原内容逐字节一致 | 高 |

---

## 7. CLI 入口测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-MAIN-01 | 无子命令 | 无 | main([]) | 返回 ExitCode.ARGUMENT_ERROR | 高 |
| TC-MAIN-02 | --version | 无 | main(["--version"]) | 输出版本号并退出 | 中 |
| TC-MAIN-03 | 解析 init | 无 | main(["init", "--vault-dir", path]) | 调用 cmd_init | 高 |
| TC-MAIN-04 | 解析 lock | 无 | main(["lock", "file.txt", "--keep"]) | 调用 cmd_lock(keep=True) | 高 |
| TC-MAIN-05 | 解析 unlock | 无 | main(["unlock", "file.txt.vault"]) | 调用 cmd_unlock | 高 |
| TC-MAIN-06 | 解析 list | 无 | main(["list", "--dir", path]) | 调用 cmd_list | 高 |

---

## 8. 错误体系测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|:---|:---|:---|:---|:---|:---|
| TC-ERR-01 | PasswordTooShortError 属性 | 无 | PasswordTooShortError(8, 3) | min_length=8, actual_length=3，消息含"3 个字符" | 高 |
| TC-ERR-02 | 异常继承链 | 无 | isinstance(err, VaultError) | 所有自定义异常均继承自 VaultError | 高 |
| TC-ERR-03 | ExitCode 枚举值 | 无 | 检查各常量 | SUCCESS=0, GENERAL_ERROR=1, ARGUMENT_ERROR=2, CRYPTO_ERROR=3, KEYSTORE_NOT_INITIALIZED=4 | 高 |
