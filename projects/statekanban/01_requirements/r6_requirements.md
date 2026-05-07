# R6 需求文档 — 虚拟底座隔离强化

| 字段 | 值 |
|------|-----|
| 轮次 | R6 |
| 主题 | 虚拟底座隔离强化 |
| 基于 | R5 已通过验证的代码基座 (`05_delivery/statekanban/`) |
| 需求数 | 5 |
| 编写角色 | PM |

---

## 背景与动机

R5 完成了 LLM 调用链路硬化和多轮驱动能力。R5 Reviewer 在 Advisory Notes 中指出：

1. **路径锚定不完整** — `Config.project_root` 虽已存在，但模块内仍有零散的 `os.getcwd()` 和硬编码相对路径，未形成统一的路径解析入口，存在沙箱逃逸风险。
2. **快照隔离缺失** — `SnapshotManager` 未按 `project_root` 隔离存储，不同项目的快照可能互相覆盖。
3. **Valve 写出路径无契约** — `OutputValve` 写出 artifact 时未强制走 `resolve_path`，路径来源不可审计。
4. **CLI 入口校验薄弱** — `--project-root` 参数仅做基础存在性检查，缺少空字节、路径逃逸、绝对路径规范化等安全校验。

R6 的目标是将"底座零 I/O"原则从引擎层扩展到全系统路径层，建立统一的虚拟底座（VirtualProjectRoot）抽象，确保所有路径操作均在 `project_root` 沙箱内完成，杜绝路径逃逸。

---

## REQ-601：VirtualProjectRoot — 路径解析统一抽象层

### 描述

在 `Config` 中引入 `VirtualProjectRoot` 抽象层。所有模块（引擎、Valve、Snapshot、Tools）的路径操作统一通过 `Config.resolve_path()` 完成，禁止直接调用 `os.getcwd()` 或手动拼接路径。`resolve_path()` 成为全系统唯一的路径解析入口，所有相对路径均相对于 `project_root` 解析。

### 验收标准

- **AC-601.1**：`Config.resolve_path(relative_path: str) -> Path` 方法存在且可调用，将相对路径解析为 `project_root / relative_path` 的绝对路径。
- **AC-601.2**：`resolve_path` 对绝对路径输入直接返回（不重定向），但记录 warning 级别日志。
- **AC-601.3**：全代码库（`05_delivery/statekanban/` 下所有 `.py` 文件）无直接 `os.getcwd()` 调用（测试文件除外）。
- **AC-601.4**：所有原本使用 `Path.cwd()` 或硬编码相对路径的位置，改为 `config.resolve_path(...)` 调用。
- **AC-601.5**：现有 R5 测试全部通过，无回归。

### 影响范围

| 文件 | 类/方法 | 变更类型 |
|------|---------|----------|
| `config.py` | `Config` | 新增 `resolve_path()` 方法，`VirtualProjectRoot` 属性 |
| `engine/engine.py` | `Engine` | 路径操作改用 `config.resolve_path()` |
| `engine/output_valve.py` | `OutputValve` | 路径操作改用 `config.resolve_path()` |
| `snapshot.py` | `SnapshotManager` | 路径操作改用 `config.resolve_path()` |
| `tools/*.py` | 各 Tool 类 | 路径操作改用 `config.resolve_path()` |
| `cli/main.py` | CLI 入口 | 路径操作改用 `config.resolve_path()` |

### 与 R5 的关系

增量变更。R5 已建立 `Config.project_root` 属性，REQ-601 在此基础上增加解析层和路径统一入口，不改动 `Config` 已有接口签名。

---

## REQ-602：Path Traversal Guard — 路径逃逸检测

### 描述

在 `Config.resolve_path()` 中增加路径逃逸检测。解析后的绝对路径若位于 `project_root` 之外（即包含 `..` 逃逸），抛出 `PathEscapeError(SK_06_001)` 错误。此检测对相对路径输入生效；绝对路径输入由 AC-601.2 的 warning 机制处理，不触发逃逸检测。

### 验收标准

- **AC-602.1**：`resolve_path("../../etc/passwd")` 抛出 `PathEscapeError`，错误码 `SK_06_001`。
- **AC-602.2**：`resolve_path("subdir/../../../etc/passwd")` 抛出 `PathEscapeError`，错误码 `SK_06_001`。
- **AC-602.3**：`resolve_path("valid/subdir/file.txt")` 正常返回 `project_root / "valid/subdir/file.txt"` 的绝对路径。
- **AC-602.4**：`resolve_path("subdir/../other/file.txt")` 正常返回（等效于 `project_root / "other/file.txt"`，未逃逸出 project_root）。
- **AC-602.5**：`PathEscapeError` 在 `core/errors.py` 中注册，错误码 `SK_06_001`，消息模板包含 attempted_path 和 project_root 信息。
- **AC-602.6**：逃逸检测在 `resolve_path` 内部以 `resolved_path.is_relative_to(project_root)` 实现，不依赖字符串匹配。

### 影响范围

| 文件 | 类/方法 | 变更类型 |
|------|---------|----------|
| `config.py` | `Config.resolve_path()` | 新增逃逸检测逻辑 |
| `core/errors.py` | 错误码注册 | 新增 `SK_06_001` PathEscapeError |

### 与 R5 的关系

增量变更。REQ-602 在 REQ-601 新增的 `resolve_path()` 方法内部增加守卫逻辑，不改变方法签名。

---

## REQ-603：Snapshot Isolation — 快照项目隔离

### 描述

`SnapshotManager` 的快照存储路径改为 `project_root / ".statekanban/snapshots/"` 下，不同 `project_root` 的快照完全隔离。移除原有的全局快照目录（如 `/tmp/statekanban/snapshots/` 或基于 cwd 的路径），确保快照生命周期与项目绑定。

### 验收标准

- **AC-603.1**：`SnapshotManager.__init__` 接受 `config: Config` 参数，从 `config.resolve_path(".statekanban/snapshots/")` 获取存储目录。
- **AC-603.2**：不同 `project_root` 的 `SnapshotManager` 实例的快照目录不同，快照列表互不可见。
- **AC-603.3**：快照文件存储在 `project_root / ".statekanban/snapshots/"` 下，不再使用系统临时目录或 cwd 相对路径。
- **AC-603.4**：原有 `SnapshotManager` 的公开接口（`save()`、`load()`、`list()`、`delete()`）签名不变。
- **AC-603.5**：`.statekanban/` 目录创建时自动写入 `.gitignore`（内容 `*`），防止快照被版本控制跟踪。

### 影响范围

| 文件 | 类/方法 | 变更类型 |
|------|---------|----------|
| `snapshot.py` | `SnapshotManager` | 构造函数改为接受 `config`，存储路径改用 `resolve_path` |
| `engine/engine.py` | `Engine` | 传递 `config` 给 `SnapshotManager` |

### 与 R5 的关系

增量变更。R5 的 `SnapshotManager` 使用固定路径，REQ-603 将其改为基于 `project_root` 的隔离存储，接口签名不变。

---

## REQ-604：Valve Path Contract — Valve 写出路径契约

### 描述

`OutputValve` 的 artifact 写出路径必须经 `config.resolve_path()` 解析。新增路径契约测试（Path Contract Test），验证所有 Valve 写出操作的路径均通过 `resolve_path` 解析，且解析后的路径位于 `project_root` 内。若 Valve 尝试写出逃逸路径，由 REQ-602 的 `PathEscapeError` 拦截。

### 验收标准

- **AC-604.1**：`OutputValve` 的所有写出方法（`write_artifact`、`flush` 等）在写出前调用 `config.resolve_path()` 解析目标路径。
- **AC-604.2**：Valve 写出路径若逃逸 `project_root`，抛出 `PathEscapeError(SK_06_001)`，artifact 不被写出。
- **AC-604.3**：新增 `test_valve_path_contract.py` 测试文件，包含以下测试用例：
  - 正常路径写出成功
  - 逃逸路径写出被拦截
  - 绝对路径写出记录 warning 但允许（与 AC-601.2 一致）
- **AC-604.4**：`OutputValve` 构造函数接受 `config: Config` 参数，用于路径解析。
- **AC-604.5**：Valve 写出后，路径解析记录以 debug 级别写入日志（含原始路径与解析后路径）。

### 影响范围

| 文件 | 类/方法 | 变更类型 |
|------|---------|----------|
| `engine/output_valve.py` | `OutputValve` | 构造函数增加 `config` 参数，写出方法改用 `resolve_path` |
| `engine/engine.py` | `Engine` | 传递 `config` 给 `OutputValve` |
| `04_testing/test_scripts/test_valve_path_contract.py` | 新增 | 路径契约测试 |

### 与 R5 的关系

增量变更。R5 的 `OutputValve` 已有写出逻辑，REQ-604 在写出前增加 `resolve_path` 解析步骤，不改变写出方法的签名和语义。

---

## REQ-605：CLI Path Validation — CLI 入口路径校验链

### 描述

CLI `--project-root` 参数增加完整路径校验链，在 `Config` 初始化之前完成校验。校验链包括：(1) 空字节检测，(2) 路径逃逸检测，(3) 相对路径转绝对路径。校验失败时给出明确错误消息并以非零退出码退出。

### 验收标准

- **AC-605.1**：`--project-root` 参数包含空字节（`\x00`）时，CLI 输出错误消息 `Path contains null byte` 并以退出码 1 退出。
- **AC-605.2**：`--project-root` 参数为相对路径时，自动转换为绝对路径（基于 `os.getcwd()` 解析，此为唯一允许的 `os.getcwd()` 调用点）。
- **AC-605.3**：`--project-root` 参数指向不存在的路径时，CLI 输出错误消息 `Project root does not exist: <path>` 并以退出码 1 退出。
- **AC-605.4**：`--project-root` 参数指向文件而非目录时，CLI 输出错误消息 `Project root is not a directory: <path>` 并以退出码 1 退出。
- **AC-605.5**：校验逻辑封装在 `cli/validate.py` 的 `validate_project_root(path_str: str) -> Path` 函数中，可独立测试。
- **AC-605.6**：新增 `test_cli_path_validation.py` 测试文件，覆盖 AC-605.1 至 AC-605.4 所有场景。
- **AC-605.7**：校验链执行顺序为：空字节检测 -> 路径规范化（相对转绝对）-> 存在性检查 -> 目录性检查。空字节检测最先执行，避免后续操作处理恶意输入。

### 影响范围

| 文件 | 类/方法 | 变更类型 |
|------|---------|----------|
| `cli/validate.py` | `validate_project_root()` | 新增校验函数 |
| `cli/main.py` | CLI 入口 | `--project-root` 校验逻辑改用 `validate_project_root()` |
| `04_testing/test_scripts/test_cli_path_validation.py` | 新增 | CLI 路径校验测试 |

### 与 R5 的关系

新功能。R5 的 CLI 仅做基础参数解析，REQ-605 新增完整的校验链和独立的校验模块。

---

## 跨 REQ 依赖关系

```
REQ-601 (VirtualProjectRoot)
  ├── REQ-602 (Path Traversal Guard) — 依赖 601 的 resolve_path
  ├── REQ-603 (Snapshot Isolation) — 依赖 601 的 resolve_path
  ├── REQ-604 (Valve Path Contract) — 依赖 601 + 602 的 resolve_path + 逃逸检测
  └── REQ-605 (CLI Path Validation) — 独立于 601，但共享校验语义
```

建议实施顺序：601 -> 602 -> 603 -> 604 -> 605

---

## 验收总则

1. 所有新增测试通过，无 skip、无 xfail。
2. R5 已有的 381+ 测试全部通过，无回归。
3. `os.getcwd()` 仅允许出现在 `cli/validate.py`（相对路径转绝对路径）中，其他位置一律禁止。
4. 新增错误码 `SK_06_001` 在 `core/errors.py` 中注册。
5. 所有路径操作经 `resolve_path` 解析，路径来源可审计。

---

## 错误码规划

| 错误码 | 名称 | 触发场景 |
|--------|------|----------|
| SK_06_001 | PathEscapeError | resolve_path 检测到路径逃逸出 project_root |

---

## 不在范围内

- 跨文件系统符号链接的深度解析（后续轮次考虑）
- 网络路径（UNC）的特殊处理
- `project_root` 运行时动态切换
- 权限模型（文件系统 ACL）
