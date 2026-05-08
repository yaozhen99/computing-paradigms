# 项目需求：StateKanban 第七轮 — 三路适配器 CLI 接入

## 项目概述

R1~R6 完成了 StateKanban 内核、引擎、隔离的全量实现（526 测试通过）。但 CLI 的 `--adapter` 选项只暴露了 `mock` 和 `codex`，三个真实 LLM 适配器均未接通。本轮目标：**接入讯飞、DeepSeek、Anthropic 三路真实 LLM，让 StateKanban 能跑真实驱动循环。**

## 适配器现状

| 适配器 | 文件 | CLI 接入 | 状态 |
|:---|:---|:---|:---|
| MockLLMAdapter | `adapters/mock_adapter.py` | `--adapter mock` | 已接入 |
| CodexAdapter | `adapters/codex_adapter.py` | `--adapter codex` | 已接入 |
| AnthropicMessagesAdapter | `adapters/anthropic_adapter.py` | 未接入 | 代码已存在 |
| ClaudeCLIAdapter | `adapters/cli_adapter.py` | 未接入 | 代码已存在 |
| IflytekAdapter | — | — | 不存在，需新建 |
| DeepSeekAdapter | — | — | 不存在，需新建 |

## 三路 LLM 接入信息

| LLM | OpenAI 兼容路由 | Anthropic 兼容路由 | 默认模型 | API Key 环境变量 |
|:---|:---|:---|:---|:---|
| 讯飞 MaaS | `IFLYTEK_BASE_URL` + `openai` SDK | — | `4.0Ultra` | `IFLYTEK_API_KEY` |
| DeepSeek | `https://api.deepseek.com` + `openai` SDK | `https://api.deepseek.com/anthropic` + `anthropic` SDK | `deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| Anthropic | — | `ANTHROPIC_BASE_URL` + `anthropic` SDK | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |

**注意**：当前环境 `ANTHROPIC_BASE_URL` 指向讯飞 MaaS 的 Anthropic 兼容端点（`https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`），不是 Anthropic 官方端点。因此 `--adapter anthropic` 实际走的是讯飞转接。如果需要直连 Anthropic 官方，需将 `ANTHROPIC_BASE_URL` 改为 `https://api.anthropic.com`。

**适配器选择指南**：

| 场景 | 命令 | 说明 |
|:---|:---|:---|
| 用讯飞模型 | `--adapter iflytek` | 走讯飞 OpenAI 兼容接口 |
| 用 DeepSeek（OpenAI 格式） | `--adapter deepseek` | 默认模式，走 OpenAI SDK |
| 用 DeepSeek（Anthropic 格式） | `--adapter deepseek --api-mode anthropic` | 走 Anthropic SDK |
| 用 Claude（讯飞转接） | `--adapter anthropic` | 当前环境默认走讯飞转接 |
| 用 Claude（直连） | `--adapter anthropic` + 改 `ANTHROPIC_BASE_URL` | 直连 Anthropic 官方 |

DeepSeek 双模式说明：
- DeepSeek API 同时兼容 OpenAI 和 Anthropic 两种 API 格式
- OpenAI 格式：`base_url=https://api.deepseek.com`，用 `openai` SDK
- Anthropic 格式：`base_url=https://api.deepseek.com/anthropic`，用 `anthropic` SDK
- 模型：`deepseek-v4-flash`（非思考）、`deepseek-v4-pro`（思考模式）
- 旧模型 `deepseek-chat`/`deepseek-reasoner` 将于 2026-07-24 弃用

## 需求条目

### REQ-701：IflytekAdapter — 讯飞 MaaS 适配器

**描述**：新建 `adapters/iflytek_adapter.py`，通过 `openai` SDK 接入讯飞 MaaS 的 OpenAI 兼容端点。

**构造参数**：
```python
class IflytekAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,       # 默认读 IFLYTEK_API_KEY
        base_url: str | None = None,       # 默认读 IFLYTEK_BASE_URL
        model: str | None = None,          # 默认读 IFLYTEK_MODEL 或 "4.0Ultra"
    )
```

**环境变量**：

| 变量 | 用途 | 示例 |
|:---|:---|:---|
| `IFLYTEK_API_KEY` | 讯飞 API 密钥 | `2eb8e6c6...` |
| `IFLYTEK_BASE_URL` | 讯飞 MaaS 端点 | `https://maas-coding-api.cn-huabei-1.xf-yun.com/v1` |
| `IFLYTEK_MODEL` | 模型名 | `4.0Ultra` |

**实现**：
1. 构造 `openai.AsyncOpenAI` 客户端
2. 转换 `LLMMessage` → OpenAI 格式
3. 调用 `client.chat.completions.create()`
4. 解析响应 → `LLMResponse`
5. 重试逻辑：RateLimitError 指数退避，其他异常重试 2 次

**验收标准**：
- AC-701.1：`IflytekAdapter` 继承 `LLMAdapter`，`complete()` 签名一致
- AC-701.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`
- AC-701.3：`IFLYTEK_API_KEY` + `IFLYTEK_BASE_URL` 设置后，`complete()` 返回有效 `LLMResponse`
- AC-701.4：RateLimitError 触发重试，最终抛出 `LLMRateLimitError`

### REQ-702：DeepSeekAdapter — DeepSeek 双模式适配器

**描述**：新建 `adapters/deepseek_adapter.py`，支持 OpenAI 和 Anthropic 两种 API 格式接入 DeepSeek。

**构造参数**：
```python
class DeepSeekAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,       # 默认读 DEEPSEEK_API_KEY
        api_mode: str | None = None,       # 默认读 DEEPSEEK_API_MODE 或 "openai"
        model: str | None = None,          # 默认读 DEEPSEEK_MODEL 或 "deepseek-v4-flash"
    )
```

**环境变量**：

| 变量 | 用途 | 默认值 |
|:---|:---|:---|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | — |
| `DEEPSEEK_API_MODE` | API 格式：`openai` 或 `anthropic` | `openai` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-v4-flash` |

**双模式实现**：

OpenAI 模式（默认）：
- `openai.AsyncOpenAI(api_key=..., base_url="https://api.deepseek.com")`
- 调用 `client.chat.completions.create(model=model, messages=...)`
- 与 IflytekAdapter 结构对称

Anthropic 模式：
- `anthropic.AsyncAnthropic(api_key=..., base_url="https://api.deepseek.com/anthropic")`
- 调用 `client.messages.create(model=model, messages=...)`
- 与 AnthropicMessagesAdapter 结构对称

**验收标准**：
- AC-702.1：`DeepSeekAdapter` 继承 `LLMAdapter`，`complete()` 签名一致
- AC-702.2：环境变量未设置时，`complete()` 抛出 `LLMAuthError`
- AC-702.3：OpenAI 模式（`api_mode="openai"`）可调用 DeepSeek API
- AC-702.4：Anthropic 模式（`api_mode="anthropic"`）可调用 DeepSeek API
- AC-702.5：`--model deepseek-v4-pro` 可切换到思考模式

### REQ-703：CLI 多适配器接入

**描述**：修改 `cli/main.py`，将 `--adapter` 选项扩展为支持全部 5 种适配器。

**变更**：
1. `--adapter` choices：`["mock", "codex", "anthropic", "iflytek", "deepseek"]`
2. `_create_adapter()` 新增 3 个分支：
   - `"anthropic"` → `AnthropicMessagesAdapter()`
   - `"iflytek"` → `IflytekAdapter()`
   - `"deepseek"` → `DeepSeekAdapter()`
3. 新增 `--model` 参数：覆盖适配器默认模型
4. 新增 `--api-mode` 参数：DeepSeek 适配器专用，选择 `openai` 或 `anthropic` 模式（默认 `openai`）
5. `adapters/__init__.py` 导出 `IflytekAdapter`、`DeepSeekAdapter`、`AnthropicMessagesAdapter`

**验收标准**：
- AC-703.1：`statekanban drive --adapter mock "test"` 正常运行（无回归）
- AC-703.2：`statekanban drive --adapter iflytek "写一个快排函数"` 用讯飞跑通
- AC-703.3：`statekanban drive --adapter deepseek "写一个快排函数"` 用 DeepSeek 跑通
- AC-703.4：`statekanban drive --adapter anthropic "test"` 用 Anthropic 跑通
- AC-703.5：`--model` 参数可覆盖默认模型名
- AC-703.6：`--api-mode anthropic` 可将 DeepSeek 切换到 Anthropic 模式

### REQ-704：真实 LLM 端到端验证

**描述**：用三路 LLM 各跑通一次驱动循环，验证 R6 隔离边界在真实 LLM 场景下生效。

**验证场景**：
1. **讯飞**：`statekanban drive --adapter iflytek --rounds 2 --verbose "写一个快排函数"` → 收敛或达到最大轮次
2. **DeepSeek**：`statekanban drive --adapter deepseek --rounds 2 --verbose "写一个快排函数"` → 收敛或达到最大轮次
3. **Anthropic**：`statekanban drive --adapter anthropic --rounds 2 --verbose "test"` → 收敛或达到最大轮次
4. **隔离**：驱动过程中 OutputValve 路径沙箱正常拦截
5. **降级**：设置极短 `--timeout`，验证 call_llm 降级响应正常
6. **快照**：`--snapshot-save snap.json`，验证快照可保存和加载

**验收标准**：
- AC-704.1：三路适配器各完成一次驱动循环，返回 `EngineResult`
- AC-704.2：FluidZone 中无 SK_EN_006 信号（无外部异常泄漏）
- AC-704.3：快照保存/加载正常

---

## 技术约束

1. **不修改 Engine 驱动循环核心逻辑** — engine.py 的 drive() 和 _process_role() 不动
2. **不修改隔离边界代码** — valve.py、read_file.py 的沙箱逻辑不动
3. **不新增 pip 依赖** — `openai`（v2.30.0）和 `anthropic` 均已安装
4. **不抽象适配器公共基类** — IflytekAdapter 和 DeepSeekAdapter 各自独立
5. **向后兼容** — `--adapter mock` 和 `--adapter codex` 行为不变

## 验收标准

1. `python -m pytest --tb=short -q` — 全量测试通过（含新增适配器测试）
2. `statekanban drive --adapter iflytek --rounds 2 "写一个快排函数"` — 讯飞端到端跑通
3. `statekanban drive --adapter deepseek --rounds 2 "写一个快排函数"` — DeepSeek 端到端跑通
4. `statekanban drive --adapter anthropic --rounds 2 "test"` — Anthropic 端到端跑通
5. `statekanban drive --adapter mock "test"` — 无回归

## 交付物清单

| # | 文件 | 操作 | 内容 |
|:---|:---|:---|:---|
| 1 | `adapters/iflytek_adapter.py` | 新增 | 讯飞 MaaS 适配器 |
| 2 | `adapters/deepseek_adapter.py` | 新增 | DeepSeek 双模式适配器 |
| 3 | `adapters/__init__.py` | 改 | 导出新适配器 + AnthropicMessagesAdapter |
| 4 | `cli/main.py` | 改 | `--adapter` 扩展 + `--model` 参数 + `--api-mode` 参数 |
| 5 | `config.py` | 改 | `llm_adapter` 选项扩展 |
| 6 | `04_testing/test_scripts/test_iflytek_adapter.py` | 新增 | IflytekAdapter 单元测试 |
| 7 | `04_testing/test_scripts/test_deepseek_adapter.py` | 新增 | DeepSeekAdapter 单元测试 |
