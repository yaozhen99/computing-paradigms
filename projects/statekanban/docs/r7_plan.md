# R7 计划：多适配器 CLI 接入 + 真实 LLM 端到端验证

> 中间文档标记：`[R7-PLAN]` — 本文件为 R7 轮次规划文档，待调度执行后归档

## Context

R1~R6 完成了 StateKanban 内核、引擎、隔离的全部实现（526 测试通过）。但 CLI 的 `--adapter` 选项只暴露了 `mock` 和 `codex`，三个真实 LLM 适配器均未接通：

- `AnthropicMessagesAdapter` — 代码已存在，CLI 未接入
- `IflytekAdapter` — **不存在**，需新建
- `OpenAICompatAdapter` — **不存在**，需新建（通用 OpenAI 兼容端点）

当前环境已有讯飞 MaaS 的 OpenAI 兼容端点配置：
- `ANTHROPIC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`
- `ANTHROPIC_AUTH_TOKEN` 已设置
- `openai` 包已安装（v2.30.0）

## 目标

1. 新建 `IflytekAdapter`（讯飞 MaaS，走 OpenAI 兼容接口）
2. 新建 `OpenAICompatAdapter`（通用 OpenAI 兼容端点，智谱/通义/DeepSeek 等）
3. CLI 接入全部适配器：`--adapter mock|codex|anthropic|iflytek|openai-compat`
4. 真实 LLM 端到端验证：用讯飞跑通 `statekanban drive`

## 适配器接口

所有适配器继承 `LLMAdapter`（`adapters/base.py`），实现：

```python
async def complete(
    self,
    messages: list[LLMMessage],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> LLMResponse
```

现有适配器：
- `MockLLMAdapter` — 确定性测试适配器
- `CodexAdapter` — Codex CLI 适配器
- `AnthropicMessagesAdapter` — Anthropic SDK 适配器（`anthropic` 包）
- `ClaudeCLIAdapter` — Claude CLI 子进程适配器

## REQ-701：IflytekAdapter — 讯飞 MaaS 适配器

### 描述

新建 `adapters/iflytek_adapter.py`，通过 `openai` SDK 接入讯飞 MaaS 的 OpenAI 兼容端点。

### 构造参数

```python
class IflytekAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,       # 默认读 IFLYTEK_API_KEY
        base_url: str | None = None,       # 默认读 IFLYTEK_BASE_URL
        model: str | None = None,          # 默认读 IFLYTEK_MODEL 或 "4.0Ultra"
    )
```

### 环境变量

| 变量 | 用途 | 示例 |
|:---|:---|:---|
| `IFLYTEK_API_KEY` | 讯飞 API 密钥 | `2eb8e6c6...` |
| `IFLYTEK_BASE_URL` | 讯飞 MaaS 端点 | `https://maas-coding-api.cn-huabei-1.xf-yun.com/v1` |
| `IFLYTEK_MODEL` | 模型名 | `4.0Ultra` |

### 实现

使用 `openai.AsyncOpenAI(api_key=..., base_url=...)` 调用，与 `AnthropicMessagesAdapter` 结构对称：
1. 构造 `openai.AsyncOpenAI` 客户端
2. 转换 `LLMMessage` → OpenAI 格式
3. 调用 `client.chat.completions.create()`
4. 解析响应 → `LLMResponse`
5. 重试逻辑：RateLimitError 指数退避，其他异常重试 2 次

### 验收标准

- AC-701.1：`IflytekAdapter` 继承 `LLMAdapter`，`complete()` 签名一致
- AC-701.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`
- AC-701.3：`IFLYTEK_API_KEY` + `IFLYTEK_BASE_URL` 设置后，`complete()` 返回有效 `LLMResponse`
- AC-701.4：RateLimitError 触发重试，最终抛出 `LLMRateLimitError`

## REQ-702：OpenAICompatAdapter — 通用 OpenAI 兼容适配器

### 描述

新建 `adapters/openai_compat_adapter.py`，通过 `openai` SDK 接入任意 OpenAI 兼容端点（智谱 GLM、通义千问、DeepSeek、Ollama 等）。

### 构造参数

```python
class OpenAICompatAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,       # 默认读 OPENAI_COMPAT_API_KEY
        base_url: str | None = None,       # 默认读 OPENAI_COMPAT_BASE_URL
        model: str | None = None,          # 默认读 OPENAI_COMPAT_MODEL 或 "gpt-4"
    )
```

### 环境变量

| 变量 | 用途 |
|:---|:---|
| `OPENAI_COMPAT_API_KEY` | API 密钥 |
| `OPENAI_COMPAT_BASE_URL` | 兼容端点 URL |
| `OPENAI_COMPAT_MODEL` | 模型名 |

### 与 IflytekAdapter 的关系

代码结构几乎相同（都用 `openai` SDK），区别仅在环境变量名和默认值。**不抽象基类**——两个文件各自独立，避免共享状态和隐式耦合。三行相似代码优于过早抽象。

### 验收标准

- AC-702.1：`OpenAICompatAdapter` 继承 `LLMAdapter`，`complete()` 签名一致
- AC-702.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`
- AC-702.3：设置后可调用任意 OpenAI 兼容端点

## REQ-703：CLI 多适配器接入

### 描述

修改 `cli/main.py`，将 `--adapter` 选项扩展为支持全部 5 种适配器。

### 变更

1. `--adapter` choices：`["mock", "codex", "anthropic", "iflytek", "openai-compat"]`
2. `_create_adapter()` 新增 3 个分支：
   - `"anthropic"` → `AnthropicMessagesAdapter()`
   - `"iflytek"` → `IflytekAdapter()`
   - `"openai-compat"` → `OpenAICompatAdapter()`
3. 新增 `--model` 参数：覆盖适配器默认模型
4. `adapters/__init__.py` 导出 `IflytekAdapter`、`OpenAICompatAdapter`、`AnthropicMessagesAdapter`

### 验收标准

- AC-703.1：`statekanban drive --adapter mock "test"` 正常运行（无回归）
- AC-703.2：`statekanban drive --adapter iflytek "写一个快排函数"` 用讯飞跑通
- AC-703.3：`statekanban drive --adapter anthropic "test"` 用 Claude API 跑通
- AC-703.4：`statekanban drive --adapter openai-compat "test"` 用通用端点跑通
- AC-703.5：`--model` 参数可覆盖默认模型名

## REQ-704：真实 LLM 端到端验证

### 描述

用讯飞 MaaS 跑通完整驱动循环，验证 R6 隔离边界在真实 LLM 场景下生效。

### 验证场景

1. **正向**：`statekanban drive --adapter iflytek --rounds 2 --verbose "写一个快排函数"` → 收敛或达到最大轮次，无异常
2. **隔离**：驱动过程中 OutputValve 路径沙箱正常拦截（真实 LLM 返回的 artifact 路径被校验）
3. **降级**：设置极短 `--timeout`，验证 call_llm 降级响应正常
4. **快照**：`--snapshot-save snap.json`，验证快照可保存和加载

### 验收标准

- AC-704.1：讯飞驱动循环完成，返回 `EngineResult`
- AC-704.2：FluidZone 中无 SK_EN_006 信号（无外部异常泄漏）
- AC-704.3：快照保存/加载正常

## 需要修改/新增的文件

| 文件 | 操作 | 内容 |
|:---|:---|:---|
| `adapters/iflytek_adapter.py` | **新增** | 讯飞 MaaS 适配器 |
| `adapters/openai_compat_adapter.py` | **新增** | 通用 OpenAI 兼容适配器 |
| `adapters/__init__.py` | 改 | 导出新适配器 |
| `cli/main.py` | 改 | `--adapter` 扩展 + `--model` 参数 |
| `config.py` | 改 | `llm_adapter` 选项扩展 |
| `04_testing/test_scripts/test_iflytek_adapter.py` | **新增** | IflytekAdapter 单元测试 |
| `04_testing/test_scripts/test_openai_compat_adapter.py` | **新增** | OpenAICompatAdapter 单元测试 |
| `04_testing/test_scripts/test_live_iflytek.py` | **新增** | 讯飞真实 API 烟雾测试（`--run-live`） |

## 不做的事

- 不抽象 IflytekAdapter 和 OpenAICompatAdapter 的公共基类
- 不修改 Engine 驱动循环逻辑
- 不修改隔离边界代码
- 不新增 pip 依赖（`openai` 已安装）

## 验证

1. `python -m pytest --tb=short -q` — 全量测试通过（含新增适配器测试）
2. `python -m pytest test_live_iflytek.py --run-live -v` — 讯飞真实 API 烟雾测试通过
3. `statekanban drive --adapter iflytek --rounds 2 --verbose "写一个快排函数"` — 端到端跑通
