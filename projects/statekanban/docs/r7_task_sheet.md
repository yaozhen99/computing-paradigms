# R7 任务表：多适配器 CLI 集成

> 轮次：R7 | 基座：R6（526 测试通过） | 日期：2026-05-08

---

## REQ-701：IflytekAdapter — 讯飞 MaaS 适配器

### 优先级
P0

### 依赖
无（可独立启动）

### 验收标准
1. AC-701.1：`IflytekAdapter` 继承 `LLMAdapter`，`complete()` 签名与基类一致
2. AC-701.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`（`SK_LLM_002`）
3. AC-701.3：`IFLYTEK_API_KEY` + `IFLYTEK_BASE_URL` 设置后，`complete()` 返回有效 `LLMResponse`
4. AC-701.4：`openai.RateLimitError` 触发指数退避重试，最终抛出 `LLMRateLimitError`（`SK_LLM_001`）
5. AC-701.5：非 RateLimit 异常重试 2 次后抛出 `LLMResponseParseError`（`SK_LLM_003`）
6. AC-701.6：构造参数优先级：显式参数 > 环境变量 > 默认值
7. AC-701.7：单元测试至少 8 个用例（正常调用、Key 缺失、RateLimit 重试、其他异常、model 覆盖、base_url 自定义、消息格式转换、响应解析）

### 实现要点

**文件**：`05_delivery/statekanban/adapters/iflytek_adapter.py`

**接口签名**：
```python
class IflytekAdapter(LLMAdapter):
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

**环境变量映射**：

| 变量 | 用途 | 示例 |
|------|------|------|
| `IFLYTEK_API_KEY` | 讯飞 API 密钥 | `2eb8e6c6...` |
| `IFLYTEK_BASE_URL` | 讯飞 MaaS 端点 | `https://maas-coding-api.cn-huabei-1.xf-yun.com/v1` |
| `IFLYTEK_MODEL` | 模型名 | `4.0Ultra` |

**实现步骤**：
1. 构造 `openai.AsyncOpenAI(api_key=..., base_url=...)` 客户端
2. 转换 `LLMMessage` → OpenAI 格式（`{"role": msg.role, "content": msg.content}`）
3. 调用 `client.chat.completions.create(model=model, messages=..., max_tokens=..., temperature=...)`
4. 解析响应 → `LLMResponse(content=..., finish_reason=..., usage=..., raw=...)`
5. 重试逻辑：`RateLimitError` 指数退避（2^attempt 秒），其他异常重试 2 次（1 秒间隔）

**技术约束**：
- 使用 `openai` SDK（v2.30.0，已安装），不引入新依赖
- 不抽象公共基类——与 `AnthropicMessagesAdapter` 结构对称但独立实现
- `tool_use`/`tool_result` 字段：IflytekAdapter 不支持 tool_use，`tools` 参数忽略并记录 warning 日志
- null bytes 校验：`complete()` 入口检查 `msg.content`，含 `\x00` 时抛 `LLMResponseParseError`

---

## REQ-702：DeepSeekAdapter — DeepSeek 双模式适配器

### 优先级
P0

### 依赖
无（可独立启动，与 REQ-701 并行）

### 验收标准
1. AC-702.1：`DeepSeekAdapter` 继承 `LLMAdapter`，`complete()` 签名与基类一致
2. AC-702.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`（`SK_LLM_002`）
3. AC-702.3：OpenAI 模式（`api_mode="openai"`）构造 `openai.AsyncOpenAI`，调用 `chat.completions.create()`
4. AC-702.4：Anthropic 模式（`api_mode="anthropic"`）构造 `anthropic.AsyncAnthropic`，调用 `messages.create()`
5. AC-702.5：`api_mode` 不为 `"openai"` 或 `"anthropic"` 时，`__init__` 抛出 `ValueError`
6. AC-702.6：`--model deepseek-v4-pro` 可切换到思考模式（仅影响 `model` 参数值，适配器内部不做特殊处理）
7. AC-702.7：两种模式均支持 `RateLimitError` 指数退避重试
8. AC-702.8：单元测试至少 10 个用例（OpenAI 正常/异常、Anthropic 正常/异常、Key 缺失、mode 校验、model 覆盖、消息转换 x2、响应解析 x2）

### 实现要点

**文件**：`05_delivery/statekanban/adapters/deepseek_adapter.py`

**接口签名**：
```python
class DeepSeekAdapter(LLMAdapter):
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

**环境变量映射**：

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | — |
| `DEEPSEEK_API_MODE` | API 格式：`openai` 或 `anthropic` | `openai` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-v4-flash` |

**双模式实现**：

OpenAI 模式（默认）：
- 客户端：`openai.AsyncOpenAI(api_key=..., base_url="https://api.deepseek.com")`
- 调用：`client.chat.completions.create(model=model, messages=..., max_tokens=..., temperature=...)`
- 消息转换：与 IflytekAdapter 结构对称
- 异常处理：`openai.RateLimitError` → 指数退避 → `LLMRateLimitError`

Anthropic 模式：
- 客户端：`anthropic.AsyncAnthropic(api_key=..., base_url="https://api.deepseek.com/anthropic")`
- 调用：`client.messages.create(model=model, messages=..., max_tokens=..., temperature=...)`
- 消息转换：与 `AnthropicMessagesAdapter._convert_messages()` 结构对称
- 异常处理：`anthropic.RateLimitError` → 指数退避 → `LLMRateLimitError`

**技术约束**：
- `api_mode` 在 `__init__` 中固定，运行时不可切换
- 不抽象公共基类——OpenAI 和 Anthropic 两条路径在同一个 `complete()` 方法内通过 `if self._api_mode == "openai"` 分支
- `tool_use` 支持：Anthropic 模式支持 `tools` 参数传递；OpenAI 模式忽略 `tools` 并记录 warning
- 旧模型名（`deepseek-chat`/`deepseek-reasoner`）在 docstring 中标注弃用提醒，代码不强制

---

## REQ-703：CLI 多适配器接入

### 优先级
P0

### 依赖
REQ-701（IflytekAdapter）、REQ-702（DeepSeekAdapter）

### 验收标准
1. AC-703.1：`statekanban drive --adapter mock "test"` 正常运行（无回归）
2. AC-703.2：`statekanban drive --adapter codex "test"` 正常运行（无回归）
3. AC-703.3：`statekanban drive --adapter anthropic "test"` 可创建 `AnthropicMessagesAdapter`
4. AC-703.4：`statekanban drive --adapter iflytek "test"` 可创建 `IflytekAdapter`
5. AC-703.5：`statekanban drive --adapter deepseek "test"` 可创建 `DeepSeekAdapter`
6. AC-703.6：`--model` 参数可覆盖适配器默认模型名
7. AC-703.7：`--adapter` 传入无效值时，CLI 报错并列出合法选项
8. AC-703.8：`--adapter` 和 `--model` 组合使用正常

### 实现要点

**文件改动**：`05_delivery/statekanban/cli/main.py`

**变更 1：扩展 `--adapter` choices**
```python
# 旧
drive_p.add_argument("--adapter", choices=["mock", "codex"], default="mock", ...)
# 新
drive_p.add_argument(
    "--adapter",
    choices=["mock", "codex", "anthropic", "iflytek", "deepseek"],
    default="mock",
    help="LLM adapter to use (default: mock)",
)
```

**变更 2：新增 `--model` 参数**
```python
drive_p.add_argument(
    "--model",
    default=None,
    help="Override adapter default model name",
)
```

**变更 3：扩展 `_create_adapter()` 函数**
```python
def _create_adapter(args: argparse.Namespace) -> Any:
    if args.adapter == "codex":
        from statekanban.adapters.codex_adapter import CodexAdapter
        return CodexAdapter()

    elif args.adapter == "anthropic":
        from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
        model = args.model or "claude-sonnet-4-20250514"
        return AnthropicMessagesAdapter(model=model)

    elif args.adapter == "iflytek":
        from statekanban.adapters.iflytek_adapter import IflytekAdapter
        model = args.model  # None → 适配器内部读环境变量或默认
        return IflytekAdapter(model=model)

    elif args.adapter == "deepseek":
        from statekanban.adapters.deepseek_adapter import DeepSeekAdapter
        model = args.model
        return DeepSeekAdapter(model=model)

    # Default: MockLLMAdapter
    from statekanban.adapters.mock_adapter import MockLLMAdapter
    if args.structured:
        return MockLLMAdapter(mode="structured")
    elif args.behavior:
        return MockLLMAdapter(mode="behavior")
    else:
        return MockLLMAdapter(mode="mock")
```

**变更 4：`adapters/__init__.py` 导出**
```python
from statekanban.adapters.base import LLMAdapter
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.adapters.codex_adapter import CodexAdapter
from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter  # 新增
from statekanban.adapters.iflytek_adapter import IflytekAdapter              # 新增
from statekanban.adapters.deepseek_adapter import DeepSeekAdapter            # 新增

__all__ = [
    "LLMAdapter",
    "MockLLMAdapter",
    "CodexAdapter",
    "AnthropicMessagesAdapter",
    "IflytekAdapter",
    "DeepSeekAdapter",
]
```

**技术约束**：
- `--adapter` 使用 `argparse` 的 `choices` 参数，无效值自动报错
- 适配器实例化使用延迟 import（在 `_create_adapter` 内 import），避免无 SDK 时影响其他适配器
- `--model` 对 mock/codex 适配器无效（静默忽略）
- 不修改 `cmd_drive()` 中 Engine 构建逻辑，仅 `_create_adapter()` 变更

---

## REQ-704：Config 适配器选项扩展

### 优先级
P1

### 依赖
REQ-701、REQ-702（需新适配器配置字段定义）

### 验收标准
1. AC-704.1：`Config.llm_adapter` 默认值仍为 `"mock"`（向后兼容）
2. AC-704.2：`Config.llm_adapter` 接受 `"iflytek"` 和 `"deepseek"` 值
3. AC-704.3：`Config.llm_model` 默认值不变，可通过 `--model` CLI 参数覆盖
4. AC-704.4：现有 Config 序列化/反序列化不受影响
5. AC-704.5：单元测试覆盖：新适配器值设置、序列化往返、默认值不变 — 至少 4 个用例

### 实现要点

**文件改动**：`05_delivery/statekanban/config.py`

**变更范围**：极小——仅更新 `llm_adapter` 字段注释和类型校验

```python
# 旧
llm_adapter: str = "mock"  # "anthropic", "cli", "mock", "codex"

# 新
llm_adapter: str = "mock"  # "anthropic", "cli", "mock", "codex", "iflytek", "deepseek"
```

**技术约束**：
- `Config` 是 dataclass，不添加新字段（`llm_adapter` 已存在，仅扩展合法值域）
- 不做硬编码校验——`llm_adapter` 的合法值由 CLI `--adapter choices` 约束，Config 层不做重复校验
- 向后兼容：现有代码读 `config.llm_adapter` 无需改动

---

## REQ-705：真实 LLM 端到端验证

### 优先级
P1

### 依赖
REQ-701、REQ-702、REQ-703（需全部适配器 + CLI 接入完成）

### 验收标准
1. AC-705.1：三路适配器各完成一次 `Engine.drive()` 循环，返回 `EngineResult`
2. AC-705.2：FluidZone 中无 `SK_EN_006` 信号（无外部异常泄漏）
3. AC-705.3：快照保存/加载正常（`--snapshot-save snap.json`）
4. AC-705.4：降级场景（极短 `--timeout`）call_llm 降级响应正常
5. AC-705.5：OutputValve 路径沙箱在真实 LLM 场景下正常拦截
6. AC-705.6：无 `IFLYTEK_API_KEY`/`DEEPSEEK_API_KEY`/`ANTHROPIC_API_KEY` 时测试 skip（非 fail）

### 实现要点

**验证场景**（手动执行 + 可选脚本）：

```bash
# 讯飞
statekanban drive --adapter iflytek --rounds 2 --verbose "写一个快排函数"

# DeepSeek (OpenAI 模式，默认)
statekanban drive --adapter deepseek --rounds 2 --verbose "写一个快排函数"

# DeepSeek (Anthropic 模式，需设 DEEPSEEK_API_MODE=anthropic)
DEEPSEEK_API_MODE=anthropic statekanban drive --adapter deepseek --rounds 2 --verbose "写一个快排函数"

# Anthropic
statekanban drive --adapter anthropic --rounds 2 --verbose "test"

# 快照
statekanban drive --adapter iflytek --rounds 2 --snapshot-save snap.json "test"

# 降级（极短超时）
statekanban drive --adapter deepseek --rounds 1 --verbose "写一个快排函数"
# (Engine._call_llm_for_role 内部 timeout 机制验证)
```

**技术约束**：
- 这是验证任务，不是测试代码编写任务（测试代码在 REQ-701/702 的单元测试中覆盖）
- 可选产出：`04_testing/test_scripts/test_live_multi_adapter.py`，标记 `@pytest.mark.live_api`
- 降级场景验证：设置极短 timeout，确认 `call_llm` 工具降级响应正常，不崩溃
- 隔离场景验证：真实 LLM 返回含路径遍历的 artifact_path 时，OutputValve 拦截

---

## REQ-706：R6 回归验证

### 优先级
P0

### 依赖
REQ-701 ~ REQ-705 全部完成

### 验收标准
1. AC-706.1：`python -m pytest --tb=short -q` 全量测试通过（含新增适配器测试）
2. AC-706.2：总测试数 >= 526（R6 基线）+ R7 新增
3. AC-706.3：无 skip、无 xfail（`live_api` 标记的除外）
4. AC-706.4：`statekanban drive --adapter mock "test"` 行为与 R6 一致（无回归）
5. AC-706.5：`statekanban drive --adapter codex "test"` 行为与 R6 一致（无回归）

### 实现要点

**无新代码**，纯验证任务。

**技术约束**：
- 若发现回归，在 R7 内修复后再验证
- 回归修复不得修改核心模块接口（Engine、Valve 等）
- 回归修复不得修改隔离边界代码（valve.py、read_file.py 沙箱逻辑）

---

## 任务依赖图

```
REQ-701 (IflytekAdapter) ──┐
                            ├──> REQ-703 (CLI 接入) ──> REQ-705 (E2E 验证) ──> REQ-706 (回归)
REQ-702 (DeepSeekAdapter) ─┘          |
                                       |
                            REQ-704 (Config 扩展)
```

## 错误码使用

R7 不新增错误码。所有适配器错误复用现有 LLM 错误体系：

| 错误类 | 错误码 | 使用场景 |
|--------|--------|----------|
| `LLMAuthError` | `SK_LLM_002` | API Key 缺失/无效 |
| `LLMRateLimitError` | `SK_LLM_001` | API 限频重试耗尽 |
| `LLMResponseParseError` | `SK_LLM_003` | 响应解析失败/其他异常重试耗尽 |

## 新增文件清单

| 文件 | REQ | 类型 |
|------|-----|------|
| `adapters/iflytek_adapter.py` | REQ-701 | 生产代码 |
| `adapters/deepseek_adapter.py` | REQ-702 | 生产代码 |
| `04_testing/test_scripts/test_iflytek_adapter.py` | REQ-701 | 单元测试 |
| `04_testing/test_scripts/test_deepseek_adapter.py` | REQ-702 | 单元测试 |
| `04_testing/test_scripts/test_live_multi_adapter.py` | REQ-705 | Live 烟雾测试（可选） |

## 修改文件清单

| 文件 | REQ | 改动范围 |
|------|-----|----------|
| `adapters/__init__.py` | REQ-703 | 新增 AnthropicMessagesAdapter / IflytekAdapter / DeepSeekAdapter 导出 |
| `cli/main.py` | REQ-703 | `--adapter` choices 扩展 + `--model` 参数 + `_create_adapter()` 新增 3 个分支 |
| `config.py` | REQ-704 | `llm_adapter` 注释更新（合法值域扩展） |

## 不修改的文件（红线）

| 文件 | 原因 |
|------|------|
| `engine/engine.py` | 不改 Engine 驱动循环核心逻辑 |
| `core/valve.py` | 不改隔离边界代码 |
| `tools/read_file.py` | 不改沙箱逻辑 |
| `adapters/base.py` | 不改基类接口 |
| `adapters/mock_adapter.py` | 不改 Mock 行为 |
| `adapters/codex_adapter.py` | 不改 Codex 行为 |
| `adapters/anthropic_adapter.py` | 不改 Anthropic 适配器（仅 CLI 接入） |
