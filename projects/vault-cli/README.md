# vault-cli

纯 CLI 离线文件加密工具。零网络依赖，口令加密，本地安全存储。

## 功能

| 命令 | 说明 |
|------|------|
| `vault init` | 初始化密钥库（生成盐值与配置文件） |
| `vault lock <file>` | 加密文件，生成 `.vault` 文件 |
| `vault unlock <file.vault>` | 解密 `.vault` 文件，还原原文件 |
| `vault list` | 列出当前目录下的 `.vault` 文件 |

## 安全特性

- AES-256-GCM 认证加密（检测口令错误与文件篡改）
- PBKDF2-SHA256 口令派生，600,000 次迭代（OWASP 2023 推荐）
- 随机盐值（16 字节），每次初始化唯一
- 随机 IV（12 字节），每次加密唯一
- 口令交互式输入，不回显，最少 8 字符
- 原子写入（临时文件 + os.rename），防止数据损坏

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误（口令不匹配、文件删除失败等） |
| 2 | 参数错误（文件不存在、路径为目录等） |
| 3 | 加密/解密错误（口令错误、认证标签校验失败等） |
| 4 | 密钥库未初始化 |

## 安装

```bash
pip install vault-cli
```

或从 wheel 包安装：

```bash
pip install vault_cli-1.0.0-py3-none-any.whl
```

验证安装：

```bash
vault --version
```

详见 [install.md](05_delivery/install.md)。

## 使用示例

```bash
# 初始化密钥库
vault init

# 加密文件（口令交互输入，不回显）
vault lock secret.txt

# 解密文件
vault unlock secret.txt.vault

# 保留原文件
vault lock secret.txt --keep
vault unlock secret.txt.vault --keep

# 查看加密文件列表
vault list
```

## .vault 文件格式

```
[版本号 4B][IV 12B][Auth Tag 16B][密文 变长]
```

- 版本号：uint32 big-endian（当前 0x00000001）
- IV：12 字节，os.urandom 生成
- Auth Tag：16 字节，AES-256-GCM 认证标签
- 密文：AES-256-GCM 加密后的原文件内容

## 技术栈

- Python 3.11+
- cryptography（AES-256-GCM + PBKDF2-SHA256）
- argparse（CLI 路由）
- 无其他外部依赖

## 测试

94 项测试全部通过，覆盖加密服务、密钥管理、文件 I/O、口令交互、CLI 命令路由、端到端往返。

## 项目边界

本系统不做：网络传输、文件夹递归加密、图形界面、多用户权限、密钥托管恢复、增量加密、格式版本迁移。

## 版本

当前版本：1.0.0。变更记录见 [changelog.md](05_delivery/changelog.md)。