# 项目需求：StateKanban 第六轮 — 虚拟底座隔离强化

## 项目概述

R5 完成了可配置项目空间路径和 R4 遗留修正。本轮目标：**强化虚拟底座与外部环境的隔离边界，使 StateKanban 内部状态机的运行不依赖、不泄漏、不被外部异常穿透。**

## 隔离现状

当前原型的架构意图正确——ToolRegistry 是唯一入口，OutputValve 是唯一出口：

```
外部世界 ← OutputValve（出口）→ 虚拟底座 ← ToolRegistry（入口）→ 外部工具
```

但存在 5 处隔离泄漏：

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| 1 | OutputValve | 写出路径无沙箱，可写任意位置（含 `../` 越界） | 高 |
| 2 | read_file 工具 | 可读任意文件，无路径限制 | 高 |
| 3 | call_llm 工具 | 网络调用无超时隔离、无重试上限，异常穿透到 Engine | 中 |
| 4 | snapshot.py | 绕过 OutputValve 独立做文件 I/O，是隔离边界外的旁路 | 中 |
| 5 | Engine._call_llm_for_role | 外部 API 异常（超时/网络错误）穿透到驱动循环，未转为内部信号 | 中 |

## 需求条目

### REQ-601：OutputValve 路径沙箱

**现在**：OutputValve 写出 artifact 时直接 `open(path)` 写入，路径无约束。

**改成**：OutputValve 写出路径必须限制在 `output_dir` 内，禁止越界。

**接口**：
```python
class OutputValve:
    def __init__(self, kanban, output_dir: str = "./output"):
        self._output_dir = os.path.abspath(output_dir)

    def _validate_path(self, path: str) -> str:
        """校验路径在 output_dir 内，返回绝对路径。越界抛 ValvePathViolationError。"""
        abs_path = os.path.abspath(os.path.join(self._output_dir, path))
        if not abs_path.startswith(self._output_dir + os.sep) and abs_path != self._output_dir:
            raise ValvePathViolationError(
                code="SK_VS_005",
                message=f"路径越界: {path} 不在 {self._output_dir} 内",
            )
        return abs_path
```

**路径校验规则**：
1. 所有写出路径必须解析为 `output_dir` 的子路径
2. `../` 越界、绝对路径指向其他目录、符号链接指向外部，均抛 `ValvePathViolationError`
3. 符号链接：解析后校验（`os.path.realpath`），防止通过符号链接逃逸
4. 错误码：`SK_VS_005`（新增）

### REQ-602：read_file 工具路径沙箱

**现在**：`read_file` 工具直接 `open(path)` 读任意文件。

**改成**：read_file 限制读取范围在 `project_root` 内。

**接口**：
```python
class ReadFileTool:
    def __init__(self, project_root: str = "."):
        self._project_root = os.path.abspath(project_root)

    def _validate_path(self, path: str) -> str:
        """校验路径在 project_root 内。越界抛 ToolPathViolationError。"""
        abs_path = os.path.abspath(os.path.join(self._project_root, path))
        if not abs_path.startswith(self._project_root + os.sep) and abs_path != self._project_root:
            raise ToolPathViolationError(
                code="SK_TR_005",
                message=f"路径越界: {path} 不在 {self._project_root} 内",
            )
        return abs_path
```

**路径校验规则**：
1. 只允许读 `project_root` 内的文件
2. 符号链接：解析后校验
3. 错误码：`SK_TR_005`（新增）
4. `project_root` 从 Config 传入，注册工具时确定

### REQ-603：call_llm 工具隔离

**现在**：call_llm 工具直接调用 adapter，无超时控制，异常直接抛出。

**改成**：call_llm 工具增加超时、重试上限、异常降级。

**接口**：
```python
class CallLLMTool:
    def __init__(self, adapter, timeout: float = 30.0, max_retries: int = 2):
        self._adapter = adapter
        self._timeout = timeout
        self._max_retries = max_retries

    async def __call__(self, messages: list, **kwargs) -> dict:
        """调用 LLM，超时/失败返回降级响应而非抛异常。"""
        for attempt in range(self._max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self._adapter.complete(messages=messages, **kwargs),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                if attempt == self._max_retries:
                    return self._fallback_response("LLM_TIMEOUT")
            except Exception:
                if attempt == self._max_retries:
                    return self._fallback_response("LLM_ERROR")

    def _fallback_response(self, reason: str) -> dict:
        """降级响应：返回空意图信号，让驱动循环继续而非崩溃。"""
        return {
            "type": "intent",
            "target_id": "task_root",
            "payload": {"action": "degraded", "reason": reason},
        }
```

**隔离规则**：
1. 超时默认 30 秒，可通过 Config 配置
2. 重试上限默认 2 次
3. 所有外部异常在工具层消化，**绝不穿透到 Engine**
4. 降级响应是合法的内部信号，驱动循环可正常处理

### REQ-604：snapshot 统一走 OutputValve

**现在**：`save_snapshot` / `load_snapshot` 直接 `open()` 读写文件，绕过 OutputValve。

**改成**：snapshot 的文件 I/O 通过 OutputValve 的受控通道执行。

**接口**：
```python
# snapshot.py 改为通过 OutputValve 写出
def save_snapshot(kanban: StateKanban, path: str, valve: OutputValve | None = None) -> None:
    """保存快照。如果提供 valve，通过 valve 写出；否则降级为直接写入（向后兼容）。"""
    data = _serialize(kanban)
    if valve is not None:
        valve.write_artifact(Artifact(
            artifact_id=make_artifact_id(),
            artifact_type=ArtifactType.CONFIG,
            author_role="system",
            content=json.dumps(data, indent=2, ensure_ascii=False),
            path=path,
            timestamp=now_utc(),
        ))
    else:
        # 向后兼容：直接写入
        _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False))

def load_snapshot(path: str, project_root: str = ".") -> StateKanban:
    """加载快照。路径校验同 read_file 沙箱规则。"""
    abs_path = os.path.abspath(os.path.join(project_root, path))
    # 校验路径在 project_root 内
    root_abs = os.path.abspath(project_root)
    if not abs_path.startswith(root_abs + os.sep) and abs_path != root_abs:
        raise SnapshotIntegrityError(code="SK_SN_003", message=f"路径越界: {path}")
    ...
```

**隔离规则**：
1. `save_snapshot` 优先走 OutputValve，享受路径沙箱保护
2. `load_snapshot` 增加路径校验，防止读取项目空间外的文件
3. 向后兼容：`valve` 参数可选，不传时降级为直接写入
4. 错误码：`SK_SN_003`（路径越界）

### REQ-605：Engine 异常边界

**现在**：Engine._call_llm_for_role 中，工具调用异常直接穿透到 drive() 循环。

**改成**：Engine 在驱动循环中捕获所有外部异常，转为内部 ErrorSignal，不中断驱动。

**接口**：
```python
async def _call_llm_for_role(self, role: str, ...) -> None:
    try:
        result = await self._registry.dispatch(tool_name, params)
        # 处理结果...
    except Exception as e:
        # 外部异常转为内部 ErrorSignal
        error_signal = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="system",
            target_id="task_root",
            payload={"error": str(e), "source": role, "code": "SK_EN_006"},
            timestamp=now_utc(),
            round_number=self._current_round,
        )
        self._kanban.fluid.write_signal(error_signal)
```

**隔离规则**：
1. Engine.drive() 的每一轮中，角色调用异常转为 ErrorSignal 写入 FluidZone
2. ErrorSignal 不中断驱动循环，由 ConvergenceDetector 统一判断
3. 连续 N 轮产生 ErrorSignal（默认 3 轮），ConvergenceDetector 判定为异常终止
4. 错误码：`SK_EN_006`（外部异常转内部信号）

---

## 技术约束

1. **不改核心模块接口**：Kanban / MessageBus / Viewport / ProcessManager 的公开方法签名不变
2. **隔离边界清晰**：所有外部 I/O 必须经过 OutputValve（写）或 ToolRegistry（读/调用），不允许旁路
3. **降级优于崩溃**：外部异常在边界层消化，返回降级信号，不让驱动循环崩溃
4. **向后兼容**：新增参数均有默认值，现有调用无需修改
5. **路径校验统一**：所有路径校验逻辑复用 Config.resolve_path() 的基准目录

## 验收标准

1. `python -m pytest 04_testing/test_scripts/ -q` — 全部通过（现有测试 + 新增隔离测试）
2. OutputValve 写出 `../etc/passwd` → 抛 `ValvePathViolationError`
3. read_file 读取 `/etc/passwd` → 抛 `ToolPathViolationError`
4. call_llm 超时 → 返回降级响应，Engine 不崩溃
5. `save_snapshot(kanban, "../outside.json", valve=valve)` → 抛路径越界错误
6. Engine 驱动中 LLM 异常 → ErrorSignal 写入 FluidZone，驱动继续
7. `python -m pytest 04_testing/test_scripts/test_isolation.py -v` — 隔离专项测试全部通过

## 交付物清单

| # | 文件 | 操作 |
|---|------|------|
| 1 | `05_delivery/statekanban/core/valve.py` | 修改：REQ-601（路径沙箱 + ValvePathViolationError） |
| 2 | `05_delivery/statekanban/core/errors.py` | 修改：REQ-601/602/604（新增 SK_VS_005、SK_TR_005、SK_SN_003、SK_EN_006） |
| 3 | `05_delivery/statekanban/tools/read_file.py` | 修改：REQ-602（路径沙箱 + ToolPathViolationError） |
| 4 | `05_delivery/statekanban/tools/call_llm.py` | 修改：REQ-603（超时 + 重试 + 降级） |
| 5 | `05_delivery/statekanban/snapshot.py` | 修改：REQ-604（走 OutputValve + 路径校验） |
| 6 | `05_delivery/statekanban/engine/engine.py` | 修改：REQ-605（异常边界 + ErrorSignal） |
| 7 | `04_testing/test_scripts/test_isolation.py` | 新增：隔离专项测试 |