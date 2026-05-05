# vault-cli 安装说明

## 系统要求

- Python >= 3.11
- pip (Python 包管理器)

## 方式一：从 PyPI 安装（推荐）

```bash
pip install vault-cli
```

## 方式二：从 Wheel 包安装

```bash
pip install vault_cli-1.0.0-py3-none-any.whl
```

## 方式三：从源码安装

```bash
# 克隆仓库后进入项目目录
cd vault-cli

# 安装构建工具
pip install build

# 构建并安装
pip install .
```

开发模式安装（可编辑）：

```bash
pip install -e .
```

## 验证安装

安装成功后，运行以下命令验证：

```bash
# 查看版本号
vault --version

# 查看帮助信息
vault --help
```

预期输出：

```
vault 1.0.0
```

```
usage: vault [-h] [--version] {init,lock,unlock,list} ...

vault-cli: 纯 CLI 离线文件加密工具

positional arguments:
  {init,lock,unlock,list}
                        可用子命令
    init                初始化密钥库
    lock                加密文件
    unlock              解密文件
    list                列出加密文件

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

## 卸载

```bash
pip uninstall vault-cli
```
