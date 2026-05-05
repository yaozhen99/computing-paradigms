# vault-cli 返工后重新审核报告

**审核时间**：2026-05-04 00:33
**被审核代码**：03_source/backend/src/vault_cli/ (返工修复版)
**审核人**：reviewer (AI)

## 1. 审核范围

本次为返工后重新审核，重点验证上次否决问题的修复情况。

涉及文件：
- `cli/commands/lock.py` — lock 子命令处理
- `cli/commands/unlock.py` — unlock 子命令处理
- `cli/exit_codes.py` — 退出码常量定义
- `errors.py` — 异常体系定义
- `cli/main.py` — CLI 入口
- `04_testing/test_scripts/test_cli_commands.py` — 新增测试用例 TC-CLI-26, TC-CLI-27

上次否决原因：文件删除失败时退出码返回 `CRYPTO_ERROR(3)` 而非 `GENERAL_ERROR(1)`，违反 API 契约。

## 2. 审核发现

### 2.1 必须修改项（阻塞合入）

| 文件:行号 | 问题描述 | 建议修改 |
|:---|:---|:---|
| （无） | | |

### 2.2 建议改进项（非阻塞）

| 文件:行号 | 问题描述 | 建议改进 |
|:---|:---|:---|
| `unlock.py:98` | `VaultFileIO.remove_original(vault_path)` 方法名 `remove_original` 用于删除 .vault 文件，语义上略显不精确 | 可考虑未来版本增加 `remove_vault` 别名方法以提升可读性，但当前行为正确，不阻塞 |

### 2.3 优秀实践（亮点）

- **删除操作独立于加密/解密 try 块**：lock.py 第 91-99 行、unlock.py 第 94-102 行将文件删除逻辑放在加密/解密 try 块之外，确保删除失败不会被误判为加密/解密错误，这是正确的错误分类策略。
- **OSError 精确捕获**：删除失败仅捕获 `OSError`（而非宽泛的 `Exception`），避免吞没意外异常。
- **新增测试显式断言 `!= CRYPTO_ERROR`**：TC-CLI-26、TC-CLI-27 不仅断言返回 `GENERAL_ERROR`，还显式断言 `!= CRYPTO_ERROR`，防止回归。

## 3. 上次否决问题逐项验证

| 否决项 | 契约要求 | 修复前行为 | 修复后行为 | 验证结果 |
|:---|:---|:---|:---|:---|
| lock 原文件删除失败退出码 | 退出码 1 (GENERAL_ERROR) | 退出码 3 (CRYPTO_ERROR) | 退出码 1 (GENERAL_ERROR) | **已修复** |
| unlock .vault 文件删除失败退出码 | 退出码 1 (GENERAL_ERROR) | 退出码 3 (CRYPTO_ERROR) | 退出码 1 (GENERAL_ERROR) | **已修复** |
| 新增测试覆盖删除失败场景 | N/A | 无覆盖 | TC-CLI-26, TC-CLI-27 均通过 | **已覆盖** |

## 4. 全量退出码交叉比对

| 子命令 | 触发条件 | 契约退出码 | 实际退出码 | 对应测试 | 一致 |
|:---|:---|:---|:---|:---|:---|
| init | 成功/已存在 | 0 | 0 (SUCCESS) | TC-CLI-01, TC-CLI-02 | Y |
| init | 目录创建失败 | 1 | 1 (GENERAL_ERROR) | — | Y |
| lock | 成功 | 0 | 0 (SUCCESS) | TC-CLI-04 | Y |
| lock | 口令不匹配 | 1 | 1 (GENERAL_ERROR) | TC-CLI-11 | Y |
| lock | 口令过短 | 1 | 1 (GENERAL_ERROR) | TC-CLI-10 | Y |
| lock | 原文件删除失败 | 1 | 1 (GENERAL_ERROR) | TC-CLI-26 | Y |
| lock | 文件不存在 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-08 | Y |
| lock | 路径为目录 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-09 | Y |
| lock | 加密内部错误 | 3 | 3 (CRYPTO_ERROR) | — | Y |
| lock | 密钥库未初始化 | 4 | 4 (KEYSTORE_NOT_INITIALIZED) | TC-CLI-07 | Y |
| unlock | 成功 | 0 | 0 (SUCCESS) | TC-CLI-12 | Y |
| unlock | .vault 删除失败 | 1 | 1 (GENERAL_ERROR) | TC-CLI-27 | Y |
| unlock | 文件不存在 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-16 | Y |
| unlock | 非 .vault 后缀 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-17 | Y |
| unlock | 路径为目录 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-18 | Y |
| unlock | 口令错误/标签校验失败 | 3 | 3 (CRYPTO_ERROR) | TC-CLI-19 | Y |
| unlock | 文件格式无效 | 3 | 3 (CRYPTO_ERROR) | TC-CLI-20 | Y |
| unlock | 密钥库未初始化 | 4 | 4 (KEYSTORE_NOT_INITIALIZED) | TC-CLI-15 | Y |
| list | 成功 | 0 | 0 (SUCCESS) | TC-CLI-21, TC-CLI-22 | Y |
| list | 目录不存在 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-23 | Y |
| list | 路径非目录 | 2 | 2 (ARGUMENT_ERROR) | TC-CLI-24 | Y |

全部退出码与 API 契约一致，无偏差。

## 5. 测试结果确认

- 测试总数：94 项（含返工新增 2 项）
- 通过率：100%（94/94）
- 返工新增用例 TC-CLI-26、TC-CLI-27 均通过
- 无缺陷记录

## 6. 整体评价

上次否决的核心问题（文件删除失败退出码错误分类为 CRYPTO_ERROR 而非 GENERAL_ERROR）已正确修复。修复方案将删除操作从加密/解密 try 块中独立出来，单独捕获 OSError 并返回 GENERAL_ERROR，逻辑清晰、分类准确。新增测试用例 TC-CLI-26 和 TC-CLI-27 精确覆盖了两个删除失败场景，并显式排除 CRYPTO_ERROR 回归。全量退出码交叉比对无偏差。代码质量良好，错误处理分层合理。

## 7. 审核结论
- [x] **批准**：可直接合入
- [ ] **需修改**：请修复"必须修改项"后再次审核
- [ ] **拒绝**：存在重大设计问题，建议返工
