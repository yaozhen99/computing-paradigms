# R7 设计文档：多适配器 CLI 集成

> 轮次：R7 | 基座：R6（526 测试通过） | 架构师产出 | 日期：2026-05-08

---

## 1. 模块变更清单

### 1.1 新增文件

| # | 文件路径 | 职责 | REQ |
|---|----------|------|-----|
| 1 | `05_delivery/statekanban/adapters/iflytek_adapter.py` | 讯飞 MaaS OpenAI 兼容适配器 | REQ-701 |
| 2 | `05_delivery/statekanban/adapters/deepseek_adapter.py` | DeepSeek 双模式（OpenAI + Anthropic）适配器 | REQ-702 |

### 1.2 修改文件

| # | 文件路径 | 改什么 | 为什么 | 怎么改 | REQ |
|---|----------|--------|--------|--------|-----|
| 1 | `adapters/__init__.py` | 新增 3 个导出 | CLI 和外部代码需按名引用适配器 | 添加 `AnthropicMessagesAdapter`、`IflytekAdapter`、`DeepSeekAdapter` 到 imports 和 `__all__` | REQ-703 |
| 2 | `cli/main.py` | `--adapter` choices 扩展 + 新增 `--model` 参数 + `_create_adapter()` 新增 3 分支 | CLI 需支持三路真实 LLM | (1) choices 从 `["mock", "codex"]` 扩展为 `["mock", "codex", "anthropic", "iflytek", "deepseek"]`； (2) 新增 `--model` 参数； (3) `_create_adapter()` 增加 anthropic/iflytek/deepseek 分支 | REQ-703 |
| 3 | `config.py` | `llm_adapter` 注释更新 | 合法值域从 4 值扩展到 6 值 | 注释从 `"anthropic", "cli", "mock", "codex"` 改为 `"anthropic", "cli", "mock", "codex", "iflytek", "deepseek"` | REQ-704 |

### 1.3 不修改的文件（红线）

| 文件 | 原因 |
|------|------|
| `adapters/base.py` | 基类接口 `LLMAdapter.complete()` 签名不动 |
| `adapters/mock_adapter.py` | Mock 行为不动 |
| `adapters/codex_adapter.py` | Codex 行为不动 |
| `adapters/anthropic_adapter.py` | Anthropic 适配器代码不动（仅 CLI 接入） |
| `adapters/cli_adapter.py` | ClaudeCLIAdapter 不动（R7 不接入） |
| `engine/engine.py` | Engine 驱动循环核心逻辑不动 |
| `core/valve.py` | 隔离边界代码不动 |
| `core/kanban.py` | 数据模型不动 |
| `core/errors.py` | 错误体系不动，复用现有 LLM 错误码 |
| `tools/call_llm.py` | call_llm 工具不动 |
| `config.py` 的 `VirtualProjectRoot` | 不动 |

---

## 2. 新增文件详细设计

### 2.1 IflytekAdapter（`adapters/iflytek_adapter.py`）

**职责**：通过 `openai` SDK 接入讯飞 MaaS 的 OpenAI 兼容端点。

**类签名**：

```python
class IflytekAdapter(LLMAdapter):
    """Iflytek MaaS adapter via OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,       # 默认读 IFLYTEK_API_KEY
        base_url: str | None = None,       # 默认读 IFLYTEK_BASE_URL
        model: str | None = None,          # 默认读 IFLYTEK_MODEL 或 "4.0Ultra"
    ) -> None: ...

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...
```

**构造参数优先级**：显式参数 > 环境变量 > 默认值

```
api_key:  args.api_key → os.environ["IFLYTEK_API_KEY"] → ""
base_url: args.base_url → os.environ["IFLYTEK_BASE_URL"] → ""
model:    args.model → os.environ["IFLYTEK_MODEL"] → "4.0Ultra"
```

**内部状态**：

```python
self._api_key: str        # 解析后的 API 密钥
self._base_url: str       # 解析后的端点 URL
self._model: str          # 解析后的模型名
self._client: openai.AsyncOpenAI | None  # 延迟初始化
```

**complete() 流程**：

```
1. 前置检查
   ├── api_key 为空 → 抛出 LLMAuthError("IFLYTEK_API_KEY not set")
   └── messages 含 \x00 → 抛出 LLMResponseParseError("Null bytes in message content")

2. 延迟初始化客户端
   └── self._client = openai.AsyncOpenAI(api_key=..., base_url=...)

3. 消息转换
   └── _convert_messages(messages) → [{"role": msg.role, "content": msg.content}, ...]

4. API 调用（重试循环，max_retries=3）
   ├── 调用 client.chat.completions.create(model=..., messages=..., max_tokens=..., temperature=...)
   ├── openai.RateLimitError → 指数退避 await asyncio.sleep(2**attempt)，重试耗尽抛出 LLMRateLimitError
   ├── openai.AuthenticationError → 直接抛出 LLMAuthError
   └── 其他 Exception → 等待 1 秒重试，耗尽抛出 LLMResponseParseError

5. 响应解析
   └── _parse_response(response) → LLMResponse

6. tools 参数处理
   └── tools 不为 None 时记录 logger.warning("IflytekAdapter does not support tool_use")，忽略
```

**消息转换方法**：

```python
@staticmethod
def _convert_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert LLMMessage list to OpenAI API format.

    IflytekAdapter 不支持 tool_use/tool_result。
    若 msg 含 tool_use 或 tool_result，将其 JSON 序列化追加到 content。
    """
    api_messages: list[dict[str, Any]] = []
    for msg in messages:
        api_msg: dict[str, Any] = {"role": msg.role}
        content = msg.content or ""
        if msg.tool_use is not None:
            content += f"\n[tool_use: {json.dumps(msg.tool_use)}]"
        if msg.tool_result is not None:
            content += f"\n[tool_result: {json.dumps(msg.tool_result)}]"
        api_msg["content"] = content
        api_messages.append(api_msg)
    return api_messages
```

**响应解析方法**：

```python
@staticmethod
def _parse_response(response: Any) -> LLMResponse:
    """Parse OpenAI API response into LLMResponse.

    Raises:
        LLMResponseParseError: If response structure is unexpected.
    """
    try:
        choice = response.choices[0]
        content = choice.message.content if choice.message else None
        finish_reason = choice.finish_reason or ""
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                "output_tokens": getattr(response.usage, "completion_tokens", 0),
            }
        return LLMResponse(
            content=content,
            finish_reason=finish_reason,
            usage=usage,
            raw=response.model_dump() if hasattr(response, "model_dump") else {},
        )
    except Exception as exc:
        raise LLMResponseParseError(f"Failed to parse Iflytek response: {exc}") from exc
```

**与 AnthropicMessagesAdapter 的结构对称性**：

| 方面 | AnthropicMessagesAdapter | IflytekAdapter |
|------|--------------------------|----------------|
| SDK | `anthropic.AsyncAnthropic` | `openai.AsyncOpenAI` |
| 客户端创建 | 每次调用新建 | 延迟初始化，复用 |
| 消息转换 | 支持 tool_use/tool_result content blocks | 降级为文本追加 |
| API 调用 | `client.messages.create()` | `client.chat.completions.create()` |
| 重试逻辑 | RateLimitError 指数退避 x3 | RateLimitError 指数退避 x3 |
| 响应解析 | 解析 content blocks (text/tool_use) | 解析 choices[0].message |
| Auth 错误 | `anthropic.AuthenticationError` | `openai.AuthenticationError` |

---

### 2.2 DeepSeekAdapter（`adapters/deepseek_adapter.py`）

**职责**：通过 OpenAI 和 Anthropic 两种 API 格式接入 DeepSeek，运行时根据 `api_mode` 选择协议。

**类签名**：

```python
class DeepSeekAdapter(LLMAdapter):
    """DeepSeek dual-mode adapter (OpenAI + Anthropic API)."""

    def __init__(
        self,
        api_key: str | None = None,       # 默认读 DEEPSEEK_API_KEY
        api_mode: str | None = None,       # 默认读 DEEPSEEK_API_MODE 或 "openai"
        model: str | None = None,          # 默认读 DEEPSEEK_MODEL 或 "deepseek-v4-flash"
    ) -> None: ...

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...
```

**构造参数优先级**：

```
api_key:  args.api_key → os.environ["DEEPSEEK_API_KEY"] → ""
api_mode: args.api_mode → os.environ["DEEPSEEK_API_MODE"] → "openai"
model:    args.model → os.environ["DEEPSEEK_MODEL"] → "deepseek-v4-flash"
```

**api_mode 校验**：

```python
# __init__ 中
if self._api_mode not in ("openai", "anthropic"):
    raise ValueError(
        f"Invalid api_mode: {self._api_mode!r}. "
        "Must be 'openai' or 'anthropic'."
    )
```

**内部状态**：

```python
self._api_key: str
self._api_mode: str         # "openai" 或 "anthropic"，构造后不可变
self._model: str
self._openai_client: openai.AsyncOpenAI | None      # 延迟初始化
self._anthropic_client: anthropic.AsyncAnthropic | None  # 延迟初始化
```

**complete() 流程**：

```
1. 前置检查
   ├── api_key 为空 → 抛出 LLMAuthError("DEEPSEEK_API_KEY not set")
   └── messages 含 \x00 → 抛出 LLMResponseParseError("Null bytes in message content")

2. 模式分发
   ├── api_mode == "openai"  → _complete_openai(messages, tools, max_tokens, temperature)
   └── api_mode == "anthropic" → _complete_anthropic(messages, tools, max_tokens, temperature)
```

**OpenAI 模式（`_complete_openai`）**：

```
1. 延迟初始化 openai.AsyncOpenAI(api_key=..., base_url="https://api.deepseek.com")
2. 消息转换 → _convert_messages_openai(messages)
3. API 调用 client.chat.completions.create(model=..., messages=..., max_tokens=..., temperature=...)
4. 重试：RateLimitError 指数退避 x3，AuthenticationError → LLMAuthError，其他重试 x2
5. 响应解析 → _parse_response_openai(response)
6. tools 参数忽略，记录 warning
```

**Anthropic 模式（`_complete_anthropic`）**：

```
1. 延迟初始化 anthropic.AsyncAnthropic(api_key=..., base_url="https://api.deepseek.com/anthropic")
2. 消息转换 → _convert_messages_anthropic(messages)
   └── 复用 AnthropicMessagesAdapter._convert_messages() 的逻辑（结构对称）
3. API 调用 client.messages.create(model=..., messages=..., max_tokens=..., temperature=...)
   └── tools 参数传递给 API（Anthropic 模式支持 tool_use）
4. 重试：RateLimitError 指数退避 x3，AuthenticationError → LLMAuthError，其他重试 x2
5. 响应解析 → _parse_response_anthropic(response)
   └── 复用 AnthropicMessagesAdapter._parse_response() 的逻辑（结构对称）
```

**消息转换方法**：

```python
@staticmethod
def _convert_messages_openai(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert LLMMessage list to OpenAI API format.

    与 IflytekAdapter._convert_messages() 逻辑一致。
    """
    api_messages: list[dict[str, Any]] = []
    for msg in messages:
        api_msg: dict[str, Any] = {"role": msg.role}
        content = msg.content or ""
        if msg.tool_use is not None:
            content += f"\n[tool_use: {json.dumps(msg.tool_use)}]"
        if msg.tool_result is not None:
            content += f"\n[tool_result: {json.dumps(msg.tool_result)}]"
        api_msg["content"] = content
        api_messages.append(api_msg)
    return api_messages

@staticmethod
def _convert_messages_anthropic(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert LLMMessage list to Anthropic API format.

    与 AnthropicMessagesAdapter._convert_messages() 结构对称。
    支持 tool_use/tool_result content blocks。
    """
    api_messages: list[dict[str, Any]] = []
    for msg in messages:
        api_msg: dict[str, Any] = {"role": msg.role}
        if msg.content is not None:
            api_msg["content"] = msg.content
        if msg.tool_use is not None:
            api_msg["content"] = [
                {"type": "tool_use", **msg.tool_use},
            ]
        if msg.tool_result is not None:
            api_msg["content"] = [
                {"type": "tool_result", **msg.tool_result},
            ]
        api_messages.append(api_msg)
    return api_messages
```

**响应解析方法**：

```python
@staticmethod
def _parse_response_openai(response: Any) -> LLMResponse:
    """Parse OpenAI-format response — 与 IflytekAdapter._parse_response() 一致。"""
    ...

@staticmethod
def _parse_response_anthropic(response: Any) -> LLMResponse:
    """Parse Anthropic-format response — 与 AnthropicMessagesAdapter._parse_response() 一致。"""
    ...
```

**DeepSeek 模型名说明**（docstring 标注，代码不强制）：

```python
"""
DeepSeek model names:
  - "deepseek-v4-flash" (default, non-thinking)
  - "deepseek-v4-pro" (thinking mode)

Deprecated (2026-07-24):
  - "deepseek-chat" → use "deepseek-v4-flash"
  - "deepseek-reasoner" → use "deepseek-v4-pro"
"""
```

---

## 3. 修改文件详细设计

### 3.1 `adapters/__init__.py`

**当前**：

```python
from statekanban.adapters.base import LLMAdapter
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.adapters.codex_adapter import CodexAdapter

__all__ = [
    "LLMAdapter",
    "MockLLMAdapter",
    "CodexAdapter",
]
```

**改为**：

```python
from statekanban.adapters.base import LLMAdapter
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.adapters.codex_adapter import CodexAdapter
from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
from statekanban.adapters.iflytek_adapter import IflytekAdapter
from statekanban.adapters.deepseek_adapter import DeepSeekAdapter

__all__ = [
    "LLMAdapter",
    "MockLLMAdapter",
    "CodexAdapter",
    "AnthropicMessagesAdapter",
    "IflytekAdapter",
    "DeepSeekAdapter",
]
```

**影响分析**：纯增量导出，不影响现有 import。

### 3.2 `cli/main.py`

#### 3.2.1 `--adapter` choices 扩展

```python
# 旧
drive_p.add_argument(
    "--adapter",
    choices=["mock", "codex"],
    default="mock",
    help="LLM adapter to use (default: mock)",
)

# 新
drive_p.add_argument(
    "--adapter",
    choices=["mock", "codex", "anthropic", "iflytek", "deepseek"],
    default="mock",
    help="LLM adapter to use (default: mock)",
)
```

**向后兼容**：`"mock"` 和 `"codex"` 行为不变。`argparse` 的 `choices` 机制自动拒绝无效值并报错。

#### 3.2.2 新增 `--model` 参数

```python
drive_p.add_argument(
    "--model",
    default=None,
    help="Override adapter default model name",
)
```

**语义**：覆盖适配器构造时的 `model` 参数。对 `mock` 和 `codex` 适配器无效（静默忽略）。

#### 3.2.3 `_create_adapter()` 扩展

```python
def _create_adapter(args: argparse.Namespace) -> Any:
    """Create the LLM adapter based on CLI arguments."""
    if args.adapter == "codex":
        from statekanban.adapters.codex_adapter import CodexAdapter
        return CodexAdapter()

    elif args.adapter == "anthropic":
        from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
        model = args.model or "claude-sonnet-4-20250514"
        return AnthropicMessagesAdapter(model=model)

    elif args.adapter == "iflytek":
        from statekanban.adapters.iflytek_adapter import IflytekAdapter
        return IflytekAdapter(model=args.model)  # None → 适配器内部读环境变量或默认

    elif args.adapter == "deepseek":
        from statekanban.adapters.deepseek_adapter import DeepSeekAdapter
        return DeepSeekAdapter(model=args.model)  # None → 适配器内部读环境变量或默认

    # Default: MockLLMAdapter
    from statekanban.adapters.mock_adapter import MockLLMAdapter
    if args.structured:
        return MockLLMAdapter(mode="structured")
    elif args.behavior:
        return MockLLMAdapter(mode="behavior")
    else:
        return MockLLMAdapter(mode="mock")
```

**关键设计决策**：

1. **延迟 import**：适配器 import 在 `_create_adapter()` 内部，避免缺少 SDK 时影响其他适配器。用户只用 mock 时无需安装 openai/anthropic。
2. **`--model` 对 Anthropic 适配器**：AnthropicMessagesAdapter 构造函数已有 `model` 参数，直接传递。
3. **`--model` 对 Iflytek/DeepSeek**：传 `model=args.model`，为 None 时适配器内部按优先级读环境变量/默认值。
4. **`--model` 对 mock/codex**：不传 model 参数，静默忽略。

### 3.3 `config.py`

**改动范围**：仅更新 `llm_adapter` 字段注释。

```python
# 旧
llm_adapter: str = "mock"  # "anthropic", "cli", "mock", "codex"

# 新
llm_adapter: str = "mock"  # "anthropic", "cli", "mock", "codex", "iflytek", "deepseek"
```

**不做硬编码校验**：`llm_adapter` 是 `str` 类型 dataclass 字段，合法值域由 CLI `--adapter choices` 约束。Config 层不重复校验，保持灵活性。

---

## 4. 接口设计汇总

### 4.1 适配器接口一览

| 适配器 | __init__ 参数 | complete() 签名 | SDK | 协议 |
|--------|--------------|-----------------|-----|------|
| MockLLMAdapter | `responses`, `structured_mode` | 基类签名 | 无 | 内存 |
| CodexAdapter | `cli_path`, `timeout` | 基类签名 | subprocess | CLI |
| AnthropicMessagesAdapter | `api_key`, `model` | 基类签名 | `anthropic` | Anthropic Messages |
| IflytekAdapter | `api_key`, `base_url`, `model` | 基类签名 | `openai` | OpenAI Chat Completions |
| DeepSeekAdapter | `api_key`, `api_mode`, `model` | 基类签名 | `openai` + `anthropic` | OpenAI / Anthropic 双模式 |

### 4.2 统一的 complete() 签名

所有适配器必须实现：

```python
async def complete(
    self,
    messages: list[LLMMessage],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> LLMResponse
```

### 4.3 统一的异常契约

| 异常类 | 错误码 | 触发条件 |
|--------|--------|----------|
| `LLMAuthError` | SK_LLM_002 | API Key 缺失/无效 |
| `LLMRateLimitError` | SK_LLM_001 | API 限频重试耗尽 |
| `LLMResponseParseError` | SK_LLM_003 | 响应解析失败/其他异常重试耗尽 |

### 4.4 tool_use 支持矩阵

| 适配器 | tools 参数 | tool_use 输出 | 说明 |
|--------|-----------|--------------|------|
| MockLLMAdapter | 忽略 | 无 | 测试用 |
| CodexAdapter | 忽略 | 无 | 子进程模式 |
| AnthropicMessagesAdapter | 传递给 API | 支持 | 完整支持 |
| IflytekAdapter | 忽略（warning） | 不支持 | 讯飞端点不支持 tool_use |
| DeepSeekAdapter (openai) | 忽略（warning） | 不支持 | OpenAI 模式暂不支持 |
| DeepSeekAdapter (anthropic) | 传递给 API | 支持 | Anthropic 模式支持 |

---

## 5. 数据流图

### 5.1 CLI 到 Engine 的完整调用链

```
用户命令
  │
  ▼
statekanban drive --adapter iflytek --model 4.0Ultra "写一个快排函数"
  │
  ▼
cli/main.py: build_parser() → 解析 args
  │  args.adapter = "iflytek"
  │  args.model = "4.0Ultra"
  │  args.intent = "写一个快排函数"
  ▼
cli/main.py: _create_adapter(args)
  │  │
  │  ├── args.adapter == "iflytek"
  │  │   └── import IflytekAdapter → IflytekAdapter(model="4.0Ultra")
  │  │       └── __init__: 读 IFLYTEK_API_KEY, IFLYTEK_BASE_URL, model="4.0Ultra"
  │  │
  │  └── 返回 adapter 实例
  ▼
cli/main.py: cmd_drive(args)
  │  1. Config() → config
  │  2. adapter = _create_adapter(args)
  │  3. StateKanban() → kanban
  │  4. MessageBus(kanban) → bus
  │  5. ToolRegistry(kanban) → registry
  │  6. OutputValve(kanban=kanban, config=config) → valve
  │  7. ViewportSlicer(kanban, specs) → slicer
  │  8. ProcessManager(kanban, bus) → pm
  │  9. Engine(kanban, bus, registry, valve, slicer, pm, adapter, config) → engine
  │  10. registry.register("call_llm", create_call_llm_tool(adapter))
  │  11. pm.create_process("coder", ...)
  ▼
Engine.drive(intent)
  │  每个 round:
  │  ├── _process_role(role)
  │  │   ├── _call_llm_for_role(role)  → 通过 adapter.complete()
  │  │   │   └── 如果 use_registry: registry.dispatch("call_llm", ...)
  │  │   │       └── CallLlmTool.__call__()
  │  │   │           └── adapter.complete(messages, tools, max_tokens, temperature)
  │  │   │               └── IflytekAdapter.complete()
  │  │   │                   ├── 前置检查（api_key, null bytes）
  │  │   │                   ├── _convert_messages(messages) → OpenAI 格式
  │  │   │                   ├── client.chat.completions.create(...)
  │  │   │                   │   ├── RateLimitError → 重试 → LLMRateLimitError
  │  │   │                   │   ├── AuthenticationError → LLMAuthError
  │  │   │                   │   └── 成功 → _parse_response() → LLMResponse
  │  │   │                   └── 返回 LLMResponse
  │  │   ├── ResponseParser.parse(response.content) → ParsedResponse
  │  │   ├── 如果是 artifact → valve.validate_and_write(artifact)
  │  │   │   └── 路径沙箱验证 → 语法检查 → 原子写入
  │  │   └── 如果是 signal → kanban.fluid.write_signal(signal)
  │  └── ConvergenceDetector.check() → 收敛/继续
  ▼
EngineResult
  │
  ▼
CLI 输出: Rounds: N, Converged: True/False
```

### 5.2 三路适配器的 API 调用路径

```
┌────────────────────────────────────────────────────────────────────┐
│                        Engine.drive()                              │
│                            │                                       │
│                    _call_llm_for_role()                            │
│                            │                                       │
│                    adapter.complete()                              │
│                            │                                       │
│              ┌─────────────┼─────────────┐                         │
│              │             │             │                         │
│    ┌─────────▼──┐  ┌──────▼──────┐  ┌──▼──────────┐              │
│    │ Iflytek    │  │ DeepSeek    │  │ Anthropic   │              │
│    │ Adapter    │  │ Adapter     │  │ Adapter     │              │
│    │            │  │             │  │             │              │
│    │ openai SDK │  │ ┌─────────┐ │  │ anthropic   │              │
│    │            │  │ │openai   │ │  │ SDK         │              │
│    │ IFLYTEK_   │  │ │SDK      │ │  │             │              │
│    │ BASE_URL   │  │ └─────────┘ │  │ ANTHROPIC_  │              │
│    │            │  │ ┌─────────┐ │  │ BASE_URL    │              │
│    │            │  │ │anthropic│ │  │             │              │
│    │            │  │ │SDK      │ │  │             │              │
│    │            │  │ └─────────┘ │  │             │              │
│    └─────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│          │                │                │                      │
└──────────┼────────────────┼────────────────┼──────────────────────┘
           │                │                │
           ▼                ▼                ▼
   讯飞 MaaS         DeepSeek API     Anthropic API
   (OpenAI 兼容)     (双模式)         (原生)
```

### 5.3 DeepSeek 双模式内部路由

```
DeepSeekAdapter.complete(messages, tools, max_tokens, temperature)
  │
  ├── api_mode == "openai"
  │   ├── _complete_openai(messages, ...)
  │   │   ├── self._openai_client (延迟初始化)
  │   │   │   └── openai.AsyncOpenAI(
  │   │   │         api_key=DEEPSEEK_API_KEY,
  │   │   │         base_url="https://api.deepseek.com"
  │   │   │       )
  │   │   ├── _convert_messages_openai(messages)
  │   │   ├── client.chat.completions.create(model, messages, ...)
  │   │   └── _parse_response_openai(response)
  │   └── tools 参数忽略
  │
  └── api_mode == "anthropic"
      ├── _complete_anthropic(messages, tools, ...)
      │   ├── self._anthropic_client (延迟初始化)
      │   │   └── anthropic.AsyncAnthropic(
      │   │         api_key=DEEPSEEK_API_KEY,
      │   │         base_url="https://api.deepseek.com/anthropic"
      │   │       )
      │   ├── _convert_messages_anthropic(messages)
      │   ├── client.messages.create(model, messages, tools, ...)
      │   └── _parse_response_anthropic(response)
      └── tools 参数传递给 API
```

---

## 6. 向后兼容性分析

### 6.1 CLI 兼容性

| 命令 | R6 行为 | R7 行为 | 兼容？ |
|------|---------|---------|--------|
| `statekanban drive --adapter mock "test"` | MockLLMAdapter(mode="mock") | 不变 | 完全兼容 |
| `statekanban drive --adapter codex "test"` | CodexAdapter() | 不变 | 完全兼容 |
| `statekanban drive --structured "test"` | MockLLMAdapter(mode="structured") | 不变 | 完全兼容 |
| `statekanban drive --behavior "test"` | MockLLMAdapter(mode="behavior") | 不变 | 完全兼容 |
| `statekanban drive "test"` (无 --adapter) | 默认 mock | 不变 | 完全兼容 |
| `statekanban drive --adapter invalid "test"` | argparse 报错 | argparse 报错（choices 扩展） | 兼容（报错信息含新选项） |

### 6.2 Config 兼容性

| 字段 | R6 | R7 | 兼容？ |
|------|----|----|--------|
| `Config.llm_adapter` 默认值 | `"mock"` | `"mock"` | 完全兼容 |
| `Config.llm_adapter` 合法值 | `"anthropic"`, `"cli"`, `"mock"`, `"codex"` | 新增 `"iflytek"`, `"deepseek"` | 增量扩展 |
| `Config.llm_model` | `"claude-sonnet-4-20250514"` | 不变 | 完全兼容 |
| `Config.to_dict()` / `from_dict()` | 不变 | 不变 | 完全兼容 |

### 6.3 适配器注册表兼容性

`adapters/__init__.py` 新增 3 个导出，`__all__` 扩展。现有 `from statekanban.adapters import LLMAdapter, MockLLMAdapter, CodexAdapter` 不受影响。

### 6.4 Engine 兼容性

Engine 构造函数接收 `adapter: LLMAdapter`，通过多态调用 `complete()`。新适配器实现相同接口，Engine 无需任何改动。

### 6.5 测试兼容性

| 测试类别 | 影响 |
|----------|------|
| R6 全量 526 测试 | 不受影响——新适配器不修改任何现有模块 |
| 新增适配器单元测试 | 独立文件，不影响现有测试 |
| `live_api` 标记测试 | 无 API Key 时 skip，不干扰 CI |

---

## 7. 风险点与缓解策略

### 7.1 讯飞 MaaS 端点不稳定

**风险**：讯飞 MaaS 的 OpenAI 兼容端点可能存在响应格式偏差（如 `choices[0].message.content` 为 `None`、`finish_reason` 返回非标准值）。

**缓解**：
- `_parse_response()` 使用 `getattr` + 默认值容错，不假设字段一定存在
- 响应原始数据保存在 `LLMResponse.raw` 中，便于调试
- `LLMResponseParseError` 捕获解析异常，不泄露到 Engine 层

### 7.2 DeepSeek 双模式复杂度

**风险**：一个适配器内含两种协议，增加维护和测试负担。`api_mode` 运行时不可切换，但用户可能混淆 `DEEPSEEK_API_MODE` 环境变量。

**缓解**：
- `__init__` 中校验 `api_mode` 值域，非法值立即 `ValueError`
- 两条代码路径各自独立的 `_convert_messages` / `_parse_response` 方法，逻辑不交叉
- 单元测试覆盖两种模式各 5 个用例，确保独立正确

### 7.3 `openai` SDK 版本兼容

**风险**：`openai` SDK v2.x 的 `RateLimitError` 位置可能在 `openai.RateLimitError` 或 `openai.types.RateLimitError`，不同子版本有差异。

**缓解**：
- 捕获 `openai.RateLimitError`（v2.30.0 确认的位置）
- 兜底：外层 `except Exception` 捕获未知异常，重试后抛出 `LLMResponseParseError`
- 建议在 `pyproject.toml` 中固定 `openai>=2.30.0`

### 7.4 延迟 import 的副作用

**风险**：`_create_adapter()` 内延迟 import，若 `openai` / `anthropic` 未安装，import 时才报错，可能令用户困惑。

**缓解**：
- IflytekAdapter 和 AnthropicMessagesAdapter 均在 `complete()` 中 import SDK 并给出明确的 `LLMAuthError` 提示（如 "openai package not installed. Run: pip install openai"）
- DeepSeekAdapter 在对应模式方法中 import，报错信息区分 OpenAI/Anthropic SDK

### 7.5 Anthropic 适配器构造函数差异

**风险**：现有 `AnthropicMessagesAdapter.__init__` 的 `model` 参数是 `str = "claude-sonnet-4-20250514"`（非 `str | None`），而 IflytekAdapter/DeepSeekAdapter 的 `model` 是 `str | None = None`。CLI 传参时需注意：

- `AnthropicMessagesAdapter(model=args.model or "claude-sonnet-4-20250514")` — 确保 model 始终有值
- `IflytekAdapter(model=args.model)` — 允许 None，适配器内部按优先级链解析
- `DeepSeekAdapter(model=args.model)` — 同上

**缓解**：在 `_create_adapter()` 中对 Anthropic 适配器做 `args.model or "claude-sonnet-4-20250514"` 兜底，不修改 `AnthropicMessagesAdapter` 构造函数。

### 7.6 null bytes 校验一致性

**风险**：现有 `CodexAdapter` 使用 `ToolRegistryError(SK_TR_004)` 校验 null bytes，而需求指定新适配器使用 `LLMResponseParseError`。

**缓解**：
- 新适配器统一使用 `LLMResponseParseError("Null bytes in message content")` 校验 null bytes
- 不修改现有 CodexAdapter 的行为（向后兼容）
- 两种异常均能被 `call_llm` 工具的 `except Exception` 兜底捕获，不会泄漏到 Engine

### 7.7 环境变量冲突

**风险**：`ANTHROPIC_BASE_URL` 同时影响 AnthropicMessagesAdapter 和 DeepSeekAdapter Anthropic 模式。

**缓解**：
- AnthropicMessagesAdapter 不传 `base_url` 参数（使用 SDK 默认读 `ANTHROPIC_BASE_URL`）
- DeepSeekAdapter Anthropic 模式显式传 `base_url="https://api.deepseek.com/anthropic"`，不依赖 `ANTHROPIC_BASE_URL`
- 两者客户端独立，互不干扰

---

## 8. 实现顺序建议

基于依赖关系图（REQ-701/702 可并行，REQ-703 依赖两者，REQ-705 依赖 REQ-703）：

```
Phase 1（并行）:
  ├── REQ-701: IflytekAdapter  ←── 无依赖
  └── REQ-702: DeepSeekAdapter ←── 无依赖

Phase 2:
  └── REQ-703: CLI 接入 ←── 依赖 Phase 1
      └── REQ-704: Config 扩展 ←── 与 REQ-703 同步

Phase 3:
  └── REQ-705: E2E 验证 ←── 依赖 Phase 2

Phase 4:
  └── REQ-706: 回归验证 ←── 依赖 Phase 3
```

---

## 9. 测试策略

### 9.1 单元测试

| 测试文件 | REQ | 用例数 | 关键场景 |
|----------|-----|--------|----------|
| `test_iflytek_adapter.py` | REQ-701 | >= 8 | 正常调用、Key 缺失、RateLimit 重试、其他异常、model 覆盖、base_url 自定义、消息格式转换、响应解析 |
| `test_deepseek_adapter.py` | REQ-702 | >= 10 | OpenAI 正常/异常、Anthropic 正常/异常、Key 缺失、mode 校验(ValueError)、model 覆盖、消息转换 x2、响应解析 x2 |

### 9.2 测试方法

- **mock SDK 客户端**：使用 `unittest.mock.AsyncMock` mock `openai.AsyncOpenAI` 和 `anthropic.AsyncAnthropic`
- **环境变量隔离**：使用 `monkeypatch` 或 `@pytest.fixture` 隔离环境变量
- **不依赖真实 API**：单元测试全部 mock，CI 可无 Key 运行

### 9.3 集成/Live 测试

| 测试文件 | 标记 | 触发条件 |
|----------|------|----------|
| `test_live_multi_adapter.py`（可选） | `@pytest.mark.live_api` | `--run-live` 参数 |

---

## 10. 错误码汇总

R7 不新增错误码。所有适配器错误复用现有体系：

| 错误类 | 错误码 | HTTP 类比 | IflytekAdapter | DeepSeekAdapter |
|--------|--------|-----------|----------------|-----------------|
| `LLMAuthError` | SK_LLM_002 | 401 | API Key 缺失/无效 | API Key 缺失/无效 |
| `LLMRateLimitError` | SK_LLM_001 | 429 | RateLimit 重试耗尽 | RateLimit 重试耗尽 |
| `LLMResponseParseError` | SK_LLM_003 | 500 | 响应解析失败/其他异常 | 响应解析失败/其他异常 |
