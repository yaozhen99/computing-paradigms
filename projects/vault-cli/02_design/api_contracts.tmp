# vault-cli API 契约定义

**版本**：v1.0
**创建时间**：2026-05-03 23:16
**架构师**：architect
**关联架构**：`02_design/architecture.md`

---

## 总则

vault-cli 为纯 CLI 工具，API 契约以子命令为接口单元。每个子命令定义：
- Endpoint：CLI 调用格式
- Request Payload：命令行参数与交互输入的结构化描述（JSON Schema 格式）
- Response Payload：标准输出与退出码的结构化描述（JSON Schema 格式）
- 错误码定义

### 通用响应结构

所有子命令共享以下响应格式：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "description": "操作是否成功" },
    "message": { "type": "string", "description": "面向用户的结果消息" },
    "exit_code": { "type": "integer", "description": "退出码" }
  },
  "required": ["success", "message", "exit_code"]
}
```

---

## 1. vault init

### Endpoint

```
vault init
```

### Request Payload

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "command": { "type": "string", "const": "init" },
    "vault_dir": {
      "type": "string",
      "description": "密钥库目录路径，默认 ~/.vault/",
      "default": "~/.vault/"
    }
  },
  "required": ["command"]
}
```

### Response Payload — 成功

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["密钥库已初始化于 ~/.vault/"] },
    "exit_code": { "type": "integer", "const": 0 },
    "data": {
      "type": "object",
      "properties": {
        "vault_dir": { "type": "string", "description": "实际创建的密钥库目录路径" },
        "salt_length": { "type": "integer", "description": "盐值长度（字节）" },
        "config": {
          "type": "object",
          "properties": {
            "algorithm": { "type": "string", "const": "AES-256-GCM" },
            "kdf": { "type": "string", "const": "PBKDF2-SHA256" },
            "iterations": { "type": "integer", "const": 600000 },
            "salt_length": { "type": "integer", "const": 16 },
            "key_length": { "type": "integer", "const": 32 },
            "iv_length": { "type": "integer", "const": 12 },
            "tag_length": { "type": "integer", "const": 16 }
          }
        }
      }
    }
  }
}
```

### Response Payload — 已初始化

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["密钥库已存在，无需重复初始化"] },
    "exit_code": { "type": "integer", "const": 0 }
  }
}
```

### 错误码

| 错误码 | 含义 | 触发条件 |
|:---|:---|:---|
| 0 | 成功 | 密钥库初始化成功或已存在 |
| 1 | 一般错误 | 密钥库目录创建失败（权限不足等） |

---

## 2. vault lock

### Endpoint

```
vault lock <file> [--keep]
```

### Request Payload

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "command": { "type": "string", "const": "lock" },
    "file": {
      "type": "string",
      "description": "待加密文件路径（相对或绝对路径）"
    },
    "keep": {
      "type": "boolean",
      "description": "是否保留原文件，默认 false（删除原文件）",
      "default": false
    },
    "password": {
      "type": "string",
      "description": "加密口令（终端交互输入，不在命令行参数中出现）",
      "minLength": 8
    }
  },
  "required": ["command", "file"]
}
```

### Response Payload — 成功

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["文件已加密：secret.txt -> secret.txt.vault"] },
    "exit_code": { "type": "integer", "const": 0 },
    "data": {
      "type": "object",
      "properties": {
        "original_file": { "type": "string", "description": "原文件路径" },
        "vault_file": { "type": "string", "description": "加密后 .vault 文件路径" },
        "original_removed": { "type": "boolean", "description": "原文件是否已删除" },
        "original_size": { "type": "integer", "description": "原文件大小（字节）" },
        "vault_size": { "type": "integer", "description": "加密文件大小（字节）" }
      }
    }
  }
}
```

### 错误码

| 错误码 | 含义 | 触发条件 |
|:---|:---|:---|
| 0 | 成功 | 文件加密成功 |
| 1 | 一般错误 | 口令不匹配（超过3次）、口令过短（不足8字符）、原文件删除失败 |
| 2 | 参数错误 | 文件路径未指定、文件不存在、文件路径为目录 |
| 3 | 加密错误 | 加密过程中发生内部错误 |
| 4 | 密钥库未初始化 | ~/.vault/ 不存在，需先执行 vault init |

---

## 3. vault unlock

### Endpoint

```
vault unlock <file.vault> [--keep]
```

### Request Payload

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "command": { "type": "string", "const": "unlock" },
    "file": {
      "type": "string",
      "description": "待解密的 .vault 文件路径",
      "pattern": "\\.vault$"
    },
    "keep": {
      "type": "boolean",
      "description": "是否保留 .vault 文件，默认 false（删除 .vault 文件）",
      "default": false
    },
    "password": {
      "type": "string",
      "description": "解密口令（终端交互输入，不在命令行参数中出现）"
    }
  },
  "required": ["command", "file"]
}
```

### Response Payload — 成功

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["文件已解密：secret.txt.vault -> secret.txt"] },
    "exit_code": { "type": "integer", "const": 0 },
    "data": {
      "type": "object",
      "properties": {
        "vault_file": { "type": "string", "description": "解密的 .vault 文件路径" },
        "restored_file": { "type": "string", "description": "还原的原始文件路径" },
        "vault_removed": { "type": "boolean", "description": ".vault 文件是否已删除" },
        "restored_size": { "type": "integer", "description": "还原文件大小（字节）" }
      }
    }
  }
}
```

### 错误码

| 错误码 | 含义 | 触发条件 |
|:---|:---|:---|
| 0 | 成功 | 文件解密成功 |
| 1 | 一般错误 | .vault 文件删除失败 |
| 2 | 参数错误 | 文件路径未指定、文件不存在、文件后缀非 .vault、文件路径为目录 |
| 3 | 解密错误 | 认证标签校验失败（口令错误或文件篡改）、.vault 文件格式无效 |
| 4 | 密钥库未初始化 | ~/.vault/ 不存在，需先执行 vault init |

---

## 4. vault list

### Endpoint

```
vault list [--dir <directory>]
```

### Request Payload

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "command": { "type": "string", "const": "list" },
    "dir": {
      "type": "string",
      "description": "扫描目录路径，默认当前工作目录",
      "default": "."
    }
  },
  "required": ["command"]
}
```

### Response Payload — 成功（有结果）

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["找到 3 个加密文件"] },
    "exit_code": { "type": "integer", "const": 0 },
    "data": {
      "type": "object",
      "properties": {
        "directory": { "type": "string", "description": "扫描的目录路径" },
        "total": { "type": "integer", "description": "加密文件总数" },
        "files": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "filename": { "type": "string", "description": ".vault 文件名" },
              "size": { "type": "integer", "description": "文件大小（字节）" },
              "encrypted_at": {
                "type": ["string", "null"],
                "format": "date-time",
                "description": "加密时间（若元数据中包含），null 表示不可用"
              }
            },
            "required": ["filename", "size", "encrypted_at"]
          }
        }
      }
    }
  }
}
```

### Response Payload — 成功（无结果）

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean", "const": true },
    "message": { "type": "string", "examples": ["当前目录下没有加密文件"] },
    "exit_code": { "type": "integer", "const": 0 },
    "data": {
      "type": "object",
      "properties": {
        "directory": { "type": "string" },
        "total": { "type": "integer", "const": 0 },
        "files": { "type": "array", "maxItems": 0 }
      }
    }
  }
}
```

### 错误码

| 错误码 | 含义 | 触发条件 |
|:---|:---|:---|
| 0 | 成功 | 列表展示成功（包括无结果的情况） |
| 2 | 参数错误 | 指定目录不存在或不是目录 |

---

## 5. 通用错误码汇总

| 退出码 | 常量名 | 含义 | 适用子命令 |
|:---|:---|:---|:---|
| 0 | `SUCCESS` | 操作成功 | init, lock, unlock, list |
| 1 | `GENERAL_ERROR` | 一般错误（口令不匹配、口令过短、文件操作失败等） | init, lock, unlock |
| 2 | `ARGUMENT_ERROR` | 参数错误（文件不存在、路径无效、后缀不符等） | lock, unlock, list |
| 3 | `CRYPTO_ERROR` | 加密/解密错误（认证标签校验失败、文件格式无效） | lock, unlock |
| 4 | `KEYSTORE_NOT_INITIALIZED` | 密钥库未初始化 | lock, unlock |

---

## 6. 口令输入协议

口令不通过命令行参数传递，统一通过终端交互输入。

### lock 命令口令输入

```
输入口令: ********        (getpass, 不回显)
确认口令: ********        (getpass, 不回显)
```

- 两次输入必须一致，不一致时提示重新输入
- 最多重试 3 次，超过后退出码 1
- 口令长度最少 8 个字符，不足时拒绝操作并退出码 1

### unlock 命令口令输入

```
输入口令: ********        (getpass, 不回显)
```

- 单次输入
- 口令错误通过 AES-GCM 认证标签校验失败来判定，非预先校验

---

## 7. .vault 文件格式契约

### 二进制布局

```
偏移量    长度          字段         类型
0x00     4 bytes      版本号       uint32 big-endian (当前值: 0x00000001)
0x04     12 bytes     IV           原始字节 (AES-GCM 推荐 12 字节)
0x10     16 bytes     Auth Tag     原始字节 (AES-GCM 16 字节认证标签)
0x20     变长          密文         AES-256-GCM 加密输出
```

### 文件头结构 (前 32 字节固定)

| 字段 | 偏移 | 长度 | 说明 |
|:---|:---|:---|:---|
| version | 0x00 | 4 | 版本号，v1 = 0x00000001 |
| iv | 0x04 | 12 | 初始化向量 |
| auth_tag | 0x10 | 16 | 认证标签 |
| ciphertext | 0x20 | N | 加密数据 |

### 格式校验规则

- 文件大小 >= 32 字节（4 + 12 + 16，即至少包含头部，密文可为空）
- 版本号必须为 0x00000001，否则返回 `VaultFileFormatError`
- IV 长度必须为 12 字节
- Auth Tag 长度必须为 16 字节

---

## 8. 密钥库文件契约

### 目录结构

```
~/.vault/
  salt.bin       # 盐值文件，16 字节二进制
  config.json    # 配置文件，JSON 格式
```

### config.json Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "version": { "type": "integer", "const": 1, "description": "配置格式版本" },
    "algorithm": { "type": "string", "const": "AES-256-GCM" },
    "kdf": { "type": "string", "const": "PBKDF2-SHA256" },
    "iterations": { "type": "integer", "const": 600000, "minimum": 600000 },
    "salt_length": { "type": "integer", "const": 16 },
    "key_length": { "type": "integer", "const": 32 },
    "iv_length": { "type": "integer", "const": 12 },
    "tag_length": { "type": "integer", "const": 16 }
  },
  "required": ["version", "algorithm", "kdf", "iterations", "salt_length", "key_length", "iv_length", "tag_length"]
}
```

### salt.bin 格式

- 16 字节原始二进制数据
- 由 `os.urandom(16)` 生成
- Linux 权限: 600 (仅当前用户可读写)
- Windows: 依赖 NTFS 默认权限

---

## 9. 加密算法参数契约

| 参数 | 值 | 依据 |
|:---|:---|:---|
| 对称加密算法 | AES-256-GCM | PRD 要求，提供认证加密 |
| 密钥长度 | 256 位 (32 字节) | AES-256 标准 |
| IV 长度 | 96 位 (12 字节) | NIST SP 800-38D 推荐 |
| Auth Tag 长度 | 128 位 (16 字节) | AES-GCM 默认，最高安全强度 |
| KDF 算法 | PBKDF2-SHA256 | PRD 要求 |
| KDF 迭代次数 | 600,000 | OWASP 2023 推荐 |
| 盐值长度 | 128 位 (16 字节) | 大于等于 16 字节，符合 NIST 建议 |
