# StateKanban R6 — 虚拟底座隔离强化

> 轮次完成日期：2026-05-08

## 概述

R6 的目标：**强化虚拟底座与外部环境的隔离边界，使 StateKanban 内部状态机的运行不依赖、不泄漏、不被外部异常穿透。**

架构意图正确——ToolRegistry 是唯一入口，OutputValve 是唯一出口：

```
外部世界 ← OutputValve（出口）→ 虚拟底座 ← ToolRegistry（入口）→ 外部工具
```

但存在 5 处隔离泄漏，本轮全部封堵。

## 核心原则

**降级优于崩溃** — 外部异常在边界层消化，返回降级信号，不让驱动循环崩溃。

## 5 处隔离泄漏与修复

### REQ-601：OutputValve 路径沙箱

| 维度 | 内容 |
|---|---|
| 问题 | 写出路径无沙箱，可写任意位置（含 `../` 越界） |
| 修复 | `_validate_path()` 校验路径在 `output_dir` 内，越界抛 `ValvePathViolationError` |
| 错误码 | SK_VS_005 |
| 严重度 | 高 |

路径校验规则：
1. 所有写出路径必须解析为 `output_dir` 的子路径
2. `../` 越界、绝对路径指向其他目录、符号链接指向外部，均抛异常
3. 符号链接：`os.path.realpath` 解析后校验，防止通过符号链接逃逸

### REQ-602：read_file 工具路径沙箱

| 维度 | 内容 |
|---|---|
| 问题 | 可读任意文件，无路径限制 |
| 修复 | `config` 参数传入 `project_root`，`resolve_path` 校验 + null-byte 检测 + symlink 校验 |
| 错误码 | SK_TR_005 |
| 严重度 | 高 |

### REQ-603：call_llm 工具隔离

| 维度 | 内容 |
|---|---|
| 问题 | 网络调用无超时隔离、无重试上限，异常穿透到 Engine |
| 修复 | `asyncio.wait_for` 超时 30s + max_retries=2 + `_fallback_response()` 降级 |
| 严重度 | 中 |

降级响应是合法的内部信号（`type: "intent"`, `action: "degraded"`），驱动循环可正常处理。

### REQ-604：snapshot 统一走 OutputValve

| 维度 | 内容 |
|---|---|
| 问题 | 绕过 OutputValve 独立做文件 I/O，是隔离边界外的旁路 |
| 修复 | `save_snapshot(valve=)` 优先走 OutputValve + `load_snapshot` 路径校验 |
| 错误码 | SK_SN_003 |
| 严重度 | 中 |

向后兼容：`valve` 参数可选，不传时降级为直接写入。

### REQ-605：Engine 异常边界

| 维度 | 内容 |
|---|---|
| 问题 | 外部 API 异常（超时/网络错误）穿透到驱动循环，未转为内部信号 |
| 修复 | 异常→`EngineExternalError` (SK_EN_006) + CLI `validate.py` 路径校验链 |
| 错误码 | SK_EN_006 |
| 严重度 | 中 |

Engine.drive() 每轮中角色调用异常转为 ErrorSignal 写入 FluidZone，不中断驱动。

## 交付物

| # | 文件 | 操作 | REQ |
|---|---|---|---|
| 1 | `core/valve.py` | 修改 | REQ-601 |
| 2 | `core/errors.py` | 修改 | REQ-601/602/604/605 |
| 3 | `tools/read_file.py` | 修改 | REQ-602 |
| 4 | `tools/call_llm.py` | 修改 | REQ-603 |
| 5 | `snapshot.py` | 修改 | REQ-604 |
| 6 | `engine/engine.py` | 修改 | REQ-605 |
| 7 | `cli/validate.py` | **新增** | REQ-605 |
| 8 | `test_isolation.py` | **新增** | 全部 |

## Reviewer 返工记录

REQ-601/602/604 各有 Critical/Major issue，返工后 PASS：

- REQ-601：`_validate_path` 需处理 Windows 路径分隔符差异 + symlink 实路径解析
- REQ-602：需增加 null-byte 检测 + `config` 参数传入 `project_root`
- REQ-604：`save_snapshot` 的 `valve` 参数需向后兼容 + `load_snapshot` 路径校验

## 验收标准

1. `python -m pytest 04_testing/test_scripts/ -q` — 全部通过
2. OutputValve 写出 `../etc/passwd` → 抛 `ValvePathViolationError`
3. read_file 读取 `/etc/passwd` → 抛 `ToolPathViolationError`
4. call_llm 超时 → 返回降级响应，Engine 不崩溃
5. `save_snapshot(kanban, "../outside.json", valve=valve)` → 抛路径越界错误
6. Engine 驱动中 LLM 异常 → ErrorSignal 写入 FluidZone，驱动继续
7. `python -m pytest 04_testing/test_scripts/test_isolation.py -v` — 隔离专项测试全部通过

## 遗留

Engine.drive() 仍是空壳（直接返回 None），驱动循环实现需后续轮次。

## 轮次历史

| 轮次 | 主题 | 状态 |
|---|---|---|
| R1 | 内核六大模块 | MISSION_ACCOMPLISHED |
| R2 | 驱动引擎+Codex接入 | MISSION_ACCOMPLISHED |
| R3 | 引擎调校+端到端验证 | MISSION_ACCOMPLISHED |
| R4 | 接口修正+真实API验证 | MISSION_ACCOMPLISHED |
| R5 | 可配置项目空间+R4遗留修正 | MISSION_ACCOMPLISHED |
| R6 | 虚拟底座隔离强化 | MISSION_ACCOMPLISHED |
