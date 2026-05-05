# CiviBBS v2.0 代码审阅材料

## README.md
# CiviBBS V2.0 — 去中心化智能体协作平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **CiviBBS = 一个让人类和AI共同参与、持续进化的去中心化智能体协作平台。**

这不是又一个AI聊天框。这是一个**基础设施**——用邮件协议让任意数量的AI智能体和人类协同工作，用插件体系让系统可插拔可进化，用流程引擎让复杂任务自动编排。

## 这个项目在做什么？

想象一个工作团队：
- **人类** 提需求、做决策
- **AI智能体** 各有所长，有的擅长代码审查，有的擅长深度分析，有的擅长快速实现
- 它们之间不靠API调用，不靠消息队列，**靠邮件通信**——就像真实世界一样

CiviBBS就是这样一个团队的操作系统。

## 已实现的核心能力

### 邮件驱动架构
所有通信都是邮件。用户发消息=发邮件，AI回复=回邮件。每封邮件有 `thread_id`（话题）和 `in_reply_to`（回复链），形成完整的对话上下文。

```
用户发邮件 → AI收件箱 → AI读取+加载历史上下文 → AI回复邮件 → 用户收件箱
```

### 三层插件体系
| 层级 | 类比 | 数量 | 示例 |
|------|------|------|------|
| L1 功能插件 | 砖头梁柱 | 51个 | read_file, atomic_write, generate_id |
| L2 流程插件 | 房间布局 | 6个 | sequence, parallel, condition, loop, retry, race |
| L3 协作体系 | 整栋建筑 | 7个 | system_init, mail_bus, topology, bbs_web |

### 流程引擎
支持顺序执行、并行执行、条件分支、循环、重试、竞争——用YAML定义流程，引擎自动编排。

### 多模式AI聊天
- **单聊**：和一个AI一对一对话，有上下文记忆
- **群聊**：多个AI同时回复，各抒己见
- **讨论**：AI依次发言，后发言的能看到前面的观点并补充

### 智能体拓扑
实时展示所有智能体的连接关系、状态、能力。智能体通过profile.json注册，随时可以加入或退出。

### 零外部依赖
纯Python标准库 + 文件系统。没有数据库，没有消息队列，没有Redis。邮件就是文件，原子移动就是锁。

## 快速开始

```bash
git clone https://github.com/yaozhen99/civibbs-v2.git
cd civibbs-v2/V2.0_play

# 启动Web服务
python -m web.app

# 访问
# http://localhost:3006      — BBS首页
# http://localhost:3006/chat — AI聊天（单聊/群聊/讨论）
# http://localhost:3006/topo — 智能体拓扑图
```

### 添加新的AI智能体

只需创建一个profile.json：

```json
{
  "id": "ai_agent_004",
  "name": "小创",
  "type": "ai",
  "icon": "🤖",
  "model": "deepseek-chat",
  "expertise": ["创意写作", "产品设计", "用户洞察"],
  "personality": "天马行空、富有想象力，喜欢从用户角度思考",
  "description": "擅长创意和产品设计的AI助手",
  "status": "online"
}
```

放到 `runtime/data/mail/agents/ai_agent_004/profile.json`，重启即可。系统自动发现、自动注册、自动加入拓扑。

## 项目结构

```
V2.0_play/
├── lib/                        # 核心库
│   ├── small/                  # L1 功能插件 (51个)
│   │   ├── fs/                 #   文件操作 (10个)
│   │   ├── cf/                 #   配置验证 (2个)
│   │   ├── lg/                 #   日志 (3个)
│   │   ├── ml/                 #   邮件操作 (8个)
│   │   ├── pt/                 #   进程线程 (18个)
│   │   ├── bb/                 #   BBS操作 (3个)
│   │   └── dt/                 #   数据转换 (7个)
│   ├── medium/                 # L2 流程插件 (6个)
│   ├── loader.py               # 插件加载器
│   ├── orchestrator.py         # 流程引擎
│   ├── ai_model.py             # AI模型管理
│   ├── mail_manager.py         # 邮件管理
│   └── topology.py             # 拓扑管理
├── runtime/                    # 运行时
│   ├── flows/                  # L3 协作体系 (7个)
│   ├── data/mail/              # 邮件存储
│   │   ├── agents/             #   智能体邮箱
│   │   ├── topo_store_*/       #   拓扑存储
│   │   └── public/             #   公共邮箱
│   └── config.yaml             # 配置
├── web/                        # Web服务
│   ├── app.py                  # Flask应用
│   └── templates/              # 页面模板
├── adapters/                   # 智能体适配器
└── docs/                       # 文档
```

## 正在建设中的

这些是我们接下来要做的，也是**最需要帮手的地方**：

| 方向 | 现状 | 需要什么 |
|------|------|---------|
| 触发机系统 | 每个插件缺少配套自测 | 为51个L1插件编写触发机 |
| 邮件协议完善 | 缺少type/context/topology标准字段 | 按设计文档补全邮件格式 |
| AC调度器 | 没有任务拆解和超时重发 | 实现AC主循环、任务分发 |
| 拓扑单元进程 | 没有独立进程和心跳 | 实现注册/心跳/ping/pong |
| 邮件总线监听 | 没有目录监听 | watchdog或inotify监听邮件到达 |
| 智能体适配器 | 未接入邮件协议 | 迁移Trae/Cursor等适配器 |
| 前端体验 | 基础可用 | 更好的UI、实时推送、邮件可视化 |

---

## 召集天下英雄

这个项目从第一天起就不是为一个人设计的。

CiviBBS的核心理念是**协作**——人类和AI协作，AI和AI协作，开发者和开发者协作。如果这个理念只停留在代码里，那就太讽刺了。我们需要真正的协作来建设它。

### 我们相信什么

1. **AI是基础设施，不是玩具** — AI不应该只在聊天框里回答问题，它应该能收邮件、处理任务、回复结果，像真实的工作者一样
2. **邮件是最朴素的协议** — 不需要gRPC，不需要消息队列，文件系统上的邮件就是最好的通信方式
3. **可插拔才有生命力** — 每个组件都能独立替换，系统才能持续进化
4. **去中心化才有韧性** — 没有单点故障，任何智能体可以下线，系统继续运转

### 我们需要什么样的人

**你不需要是AI专家。** 这个项目的大部分工作是传统软件工程：

- **Python开发者** — 写插件、写流程定义、写测试。51个L1插件需要触发机，6个L2执行器需要完善，7个L3流程需要验证
- **前端开发者** — 聊天界面、拓扑可视化、邮件浏览器、管理后台。当前UI是功能性的，需要有人让它变得好用
- **系统架构师** — AC调度器设计、拓扑协议完善、邮件总线优化。如果你喜欢分布式系统的纯粹感，这里很适合你
- **AI应用开发者** — 接入更多模型（Gemini、Llama、Qwen）、优化prompt策略、实现智能体记忆和规划
- **文档写作者** — 把设计文档变成开发者指南，写教程，录演示
- **测试工程师** — 端到端测试、并发测试、故障注入测试。邮件系统的原子竞争需要严格验证
- **设计师** — 拓扑图的交互设计、邮件流的可视化、智能体卡片的设计语言

### 怎么参与

1. **Fork → 改 → PR** — 最经典的方式。哪怕修一个bug、补一个触发机、写一段文档，都是贡献
2. **领一个方向** — 从上面的"正在建设中"表格里选一个方向，在Issue里说"我来做"，然后开干
3. **提建议** — 如果你觉得架构有问题、设计有缺陷，开Issue讨论。好的批评比坏的PR更有价值
4. **写插件** — 按照插件规范写一个新的L1插件，附带触发机，提交PR。这是最好的入门方式
5. **做适配器** — 把你常用的AI工具（Trae、Cursor、Windsurf等）接入CiviBBS的邮件系统

### 贡献者将获得

- 在README和文档中永久署名
- 对项目方向的发言权
- 一个真正有趣的、有深度的开源项目
- 和一群相信"AI是基础设施"的人一起工作的机会

### 第一个PR的建议

最容易上手的贡献：

1. **为一个L1插件写触发机** — 选一个 `lib/small/` 下的插件，读它的definition.yaml，写2-3个测试场景
2. **补全邮件格式** — 在mail_manager.py中添加type/context/topology字段
3. **改进拓扑图** — 加动画、加交互、加邮件流可视化
4. **写一个新AI智能体** — 创建profile.json，定义个性、专长、模型

---

## 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| 语言 | Python 3.10+ | 跨平台，AI生态最丰富 |
| 通信 | 文件系统邮件 | 零依赖，原子操作，天然持久化 |
| Web | Flask | 轻量，够用 |
| AI模型 | DeepSeek / 星火 / Anthropic / Ollama | 可插拔，按需选择 |
| 配置 | YAML | 人类可读 |
| 测试 | pytest + 触发机 | 每个插件独立可验证 |

## 许可证

MIT License — 随便用，随便改，随便分发。唯一要求：保留版权声明。

## 作者

Yao Zhen — 一个相信AI应该像邮件一样朴素、像插件一样可替换的人。

Email: yaozhen99@gmail.com
GitHub: @yaozhen99

## 致谢

感谢每一个愿意相信"AI是基础设施"这个理念的人。

这个项目从2026年1月开始，从一个简单的想法出发：**如果AI能像收邮件一样工作，世界会怎样？**

现在我们有了初步的答案。但真正的答案，需要更多人一起写。

---

**首发：2026年3月** | **当前版本：2.0-alpha** | **开发时间：4个月**

**如果你读到这里，说明你感兴趣。那就来吧。**


## docs/v2_gap_analysis.md
---
name: v2-gap-analysis
description: V2.0当前实现与设计目标的差距分析
type: project
---

# V2.0 实现差距分析

## 对照核心文件的标准

### 已实现 ✅
| 设计要求 | 当前实现 | 完成度 |
|---------|---------|--------|
| 三层插件体系(L1/L2/L3) | lib/small(51个) + lib/medium(6个) + runtime/flows(7个) | 90% |
| 引擎(orchestrator) | 支持sequence/condition/parallel/loop/retry/race | 90% |
| 插件加载器(loader) | 动态加载small和medium | 90% |
| 邮件系统基础 | mail_manager.py + agents目录结构 | 60% |
| 拓扑存储 | topology.py + topo_store + 副本机制 | 50% |
| AI聊天(邮件驱动) | /api/chat走邮件协议,thread_id,in_reply_to | 70% |
| 拓扑可视化 | /topo页面,SVG圆形布局 | 40% |
| Web服务 | Flask + BBS讨论 + 健康检查 | 70% |

### 未实现 ❌
| 设计要求 | 差距 | 优先级 |
|---------|------|--------|
| 触发机(triggers) | 每个插件缺少配套触发机,无法自测验证 | 高 |
| 邮件格式标准 | 缺少type(task/result/register/ping等)、context、topology字段 | 高 |
| AC调度器 | 没有AC主循环、任务拆解、超时重发 | 高 |
| 拓扑单元进程 | 没有独立进程,没有心跳/ping/pong机制 | 中 |
| 邮件总线监听(watchdog) | 没有目录监听,邮件到达无通知 | 中 |
| 智能体适配器 | adapters/base_adapter.py未接入邮件协议 | 中 |
| 流程定义验证 | 没有流程定义的语法检查和验证 | 低 |
| 模型微调闭环 | BBS数据→微调→更强,这个是远期目标 | 低 |

## 邮件格式差距(核心文件标准 vs 当前实现)

标准邮件格式:
- msg_id, from, to, in_reply_to, thread_id ✅
- type (task/result/progress/register/ping/pong/shutdown/cancel/topology_data) ❌ 缺少
- context (task_type, priority, deadline, requirements, agent_type, capabilities, doc_id, author, workspace, file_tree) ❌ 缺少
- topology (storage, units) ❌ 缺少
- timestamp ✅
- expires, completed ❌ 缺少

## 值不值得放GitHub?

**值得放,理由:**
1. 核心架构已成型:三层插件+引擎+邮件总线,这是最难的部分
2. 邮件驱动聊天已跑通:thread_id上下文、AI间讨论,这是差异化亮点
3. 拓扑可视化已可用:4个智能体实时展示
4. 比V1.0的6个空记录强太多:有实际可运行的代码

**建议:**
- 放到公开库,标明 v2.0-alpha 或 v2.0-preview
- README写清楚:已实现什么、待实现什么
- 核心文件(系统核心文件-*)应该放进docs/作为设计文档
- 不需要完美才发布,开源项目本身就是持续进化的过程


## docs/progress_2026_04_21.md
---
name: v2-progress-2026-04-21
description: V2.0开发进展总结（截至2026-04-21）
type: project
---

# V2.0 开发进展总结（2026-04-21）

## 已完成

### 核心架构
- 三层插件体系：L1功能插件51个 + L2流程插件6个 + L3协作流程7个
- 流程引擎（orchestrator.py）：支持sequence/parallel/condition/loop/retry/race
- 插件加载器（loader.py）：动态加载small和medium插件
- AI模型管理（ai_model.py）：支持DeepSeek-chat、DeepSeek-reasoner、星火

### 邮件驱动架构
- mail_manager.py：邮件创建、投递、读取、线程加载
- 邮件协议：msg_id, thread_id, in_reply_to, from, to, timestamp
- AI聊天走邮件协议：用户消息=发邮件，AI回复=回邮件，thread_id维持上下文
- 三种聊天模式：单聊、群聊、讨论

### 拓扑系统
- topology.py：智能体注册、心跳、拓扑存储（带副本）
- scan_profiles()：从profile.json自动发现和注册智能体
- 拓扑可视化页面（/topo）：SVG圆形布局，实时刷新

### 智能体
- ai_agent_001（小智）：deepseek-chat，务实直接
- ai_agent_002（小慧）：deepseek-reasoner，严谨深思
- ai_agent_003（Claude）：deepseek-chat，温和细致
- human_user（用户）：人类智能体

### Web服务
- Flask应用：BBS首页、AI聊天、拓扑图
- API：/api/agents、/api/chat、/api/topo、/api/topo/refresh

### GitHub发布准备
- README.md：项目介绍+招募文档
- .gitignore：排除config.yaml（含API密钥）和运行时数据
- config.example.yaml：密钥占位符版本
- LICENSE：MIT
- docs/core/：9个核心设计文档（从核心文件目录整理）

## 未实现（差距分析）

| 项目 | 优先级 | 说明 |
|------|--------|------|
| 触发机系统 | 高 | 51个L1插件缺少配套触发机 |
| 邮件格式标准 | 高 | 缺少type/context/topology字段 |
| AC调度器 | 高 | 没有任务拆解和超时重发 |
| 拓扑单元进程 | 中 | 没有独立进程和心跳 |
| 邮件总线监听 | 中 | 没有watchdog目录监听 |
| 智能体适配器 | 中 | adapters未接入邮件协议 |
| 流程定义验证 | 低 | 没有语法检查 |
| 模型微调闭环 | 低 | 远期目标 |

## 关键决策记录

1. AI智能体从profile.json动态加载，不硬编码
2. 同一模型+不同个性=不同行为（小智和Claude都用deepseek-chat）
3. 邮件驱动聊天：每条消息都是邮件，thread_id维持上下文
4. Anthropic API不可用，Claude智能体暂用deepseek-chat+不同个性
5. 代码中移除所有"姚震"姓名
6. GitHub发布标为v2.0-alpha
7. Git提交在有VPN的虚拟机进行，开发环境不提交


## lib/orchestrator.py
"""
引擎核心 - 解析流程定义，执行节点，管理上下文
支持：循环(for)、数组索引、条件分支、并行执行(parallel)
"""

import logging
import re
import ast
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class Orchestrator:
    """流程编排器"""

    def __init__(self, loader):
        self.loader = loader
        self.context: Dict[str, Any] = {}

    def run(self, flow_def: Dict, external_inputs: Dict = None) -> Dict:
        """执行流程定义"""
        self.context = {"external": external_inputs or {}}

        steps = flow_def.get("steps", [])
        for step in steps:
            result = self._execute_step(step)

            outputs = step.get("outputs", {})
            for key, var_name in outputs.items():
                if isinstance(result, dict) and key in result:
                    self.context[var_name] = result[key]
                else:
                    self.context[var_name] = result

        return self.context

    def _execute_step(self, step: Dict) -> Any:
        """执行单个步骤"""
        step_type = step.get("type", "plugin")

        if step_type == "plugin":
            return self._execute_plugin(step)
        elif step_type == "condition":
            return self._execute_condition(step)
        elif step_type == "parallel":
            return self._execute_parallel(step)
        elif step_type == "for":
            return self._execute_for_loop(step)
        elif step_type == "loop":
            return self._execute_loop(step)
        elif step_type == "retry":
            return self._execute_retry(step)
        elif step_type == "race":
            return self._execute_race(step)
        else:
            raise ValueError(f"未知步骤类型: {step_type}")

    def _execute_plugin(self, step: Dict) -> Dict:
        """执行 small 插件"""
        plugin_name = step.get("plugin")
        if not plugin_name:
            raise ValueError("步骤缺少 plugin 字段")

        inputs = step.get("inputs", {})
        resolved_inputs = self._resolve_inputs(inputs)

        plugin = self.loader.load_small(plugin_name)
        logger.debug(f"执行插件: {plugin_name}")

        try:
            result = plugin(resolved_inputs)
            return result
        except Exception as e:
            on_error = step.get("on_error")
            if on_error == "continue":
                logger.warning(f"插件执行失败，继续: {plugin_name}, {e}")
                return step.get("error_output", {})
            elif on_error == "break":
                logger.warning(f"插件执行失败，中断: {plugin_name}, {e}")
                raise
            raise

    def _execute_condition(self, step: Dict) -> Dict:
        """执行条件分支"""
        condition_str = step.get("condition")
        if not condition_str:
            raise ValueError("条件分支缺少 condition 字段")

        condition = self._evaluate_condition(condition_str)

        if condition:
            branch = step.get("true_branch", [])
        else:
            branch = step.get("false_branch", [])

        results = {}
        for sub_step in branch:
            result = self._execute_step(sub_step)
            if isinstance(result, dict):
                results.update(result)
            # 处理子步骤的 outputs
            outputs = sub_step.get("outputs", {})
            for key, var_name in outputs.items():
                if isinstance(result, dict) and key in result:
                    self.context[var_name] = result[key]

        results["executed_branch"] = "true" if condition else "false"
        return results

    def _execute_parallel(self, step: Dict) -> Dict:
        """并行执行（使用线程池）"""
        steps = step.get("steps", [])
        max_workers = step.get("max_workers", len(steps))
        fail_fast = step.get("fail_fast", True)

        results = {}
        errors = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, sub_step in enumerate(steps):
                context_copy = self.context.copy()
                future = executor.submit(self._execute_step_with_context, sub_step, context_copy)
                futures[future] = i

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    results[f"step_{idx}"] = result
                except Exception as e:
                    errors[f"step_{idx}"] = str(e)
                    if fail_fast:
                        for f in futures:
                            f.cancel()
                        raise

        return {
            "results": results,
            "errors": errors,
            "all_success": len(errors) == 0
        }

    def _execute_step_with_context(self, step: Dict, context: Dict) -> Dict:
        """使用独立上下文执行步骤"""
        original_context = self.context
        self.context = context
        try:
            result = self._execute_step(step)
            return result
        finally:
            self.context = original_context

    def _execute_for_loop(self, step: Dict) -> Dict:
        """循环执行"""
        items = step.get("items")
        if not items:
            raise ValueError("循环缺少 items 字段")

        as_var = step.get("as", "item")
        index_as = step.get("index_as")
        steps = step.get("steps", [])

        if isinstance(items, str) and items.startswith("${") and items.endswith("}"):
            items = self._resolve_ref(items[2:-1])
        if not isinstance(items, list):
            raise ValueError(f"items 必须是列表，实际: {type(items)}")

        before_keys = set(self.context.keys())
        results = []

        for idx, item in enumerate(items):
            self.context[as_var] = item
            if index_as:
                self.context[index_as] = idx

            for sub_step in steps:
                self._execute_step(sub_step)

            new_keys = set(self.context.keys()) - before_keys
            iteration_result = {k: self.context[k] for k in new_keys}
            results.append(iteration_result)

            for key in new_keys:
                del self.context[key]

        outputs = step.get("outputs", {})
        if outputs:
            result_var = outputs.get("results")
            if result_var:
                self.context[result_var] = results

        return {"iterations": len(results), "results": results}

    def _execute_loop(self, step: Dict) -> Dict:
        """循环执行直到条件满足"""
        condition = step.get("condition")
        max_iterations = step.get("max_iterations", 100)
        steps = step.get("steps", [])

        iterations = 0
        while iterations < max_iterations:
            for sub_step in steps:
                self._execute_step(sub_step)

            if self._evaluate_condition(condition):
                break
            iterations += 1

        return {"iterations": iterations, "completed": iterations < max_iterations}

    def _execute_retry(self, step: Dict) -> Dict:
        """重试执行"""
        max_retries = step.get("max_retries", 3)
        delay = step.get("delay", 1)
        steps = step.get("steps", [])

        last_error = None
        for attempt in range(max_retries):
            try:
                results = {}
                for sub_step in steps:
                    result = self._execute_step(sub_step)
                    if isinstance(result, dict):
                        results.update(result)
                return {"success": True, "attempts": attempt + 1, "results": results}
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(delay)

        return {"success": False, "attempts": max_retries, "error": str(last_error)}

    def _execute_race(self, step: Dict) -> Dict:
        """竞争执行（第一个成功即返回）"""
        steps = step.get("steps", [])

        with ThreadPoolExecutor(max_workers=len(steps)) as executor:
            futures = {}
            for i, sub_step in enumerate(steps):
                context_copy = self.context.copy()
                future = executor.submit(self._execute_step_with_context, sub_step, context_copy)
                futures[future] = i

            for future in as_completed(futures):
                try:
                    result = future.result()
                    return {"winner": futures[future], "result": result, "success": True}
                except Exception:
                    continue

        return {"success": False, "error": "所有分支都失败"}

    def _resolve_inputs(self, inputs: Dict) -> Dict:
        """解析输入中的 ${} 引用，支持 range() 函数"""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]
                if ref.startswith("range(") and ref.endswith(")"):
                    resolved[key] = self._eval_range(ref)
                else:
                    resolved[key] = self._resolve_ref(ref)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_inputs(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_ref(v[2:-1]) if isinstance(v, str) and v.startswith("${") and v.endswith("}") else v
                    for v in value
                ]
            else:
                resolved[key] = value
        return resolved

    def _resolve_ref(self, ref: str) -> Any:
        """解析引用，支持嵌套、数组索引"""
        current = self.context

        parts = ref.split(".")

        for part in parts:
            if current is None:
                return None

            if "[" in part and part.endswith("]"):
                base, idx_str = part.split("[")
                idx = int(idx_str.rstrip("]"))

                if isinstance(current, dict):
                    current = current.get(base)
                else:
                    return None

                if isinstance(current, list) and -len(current) <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        return current

    def _eval_range(self, expr: str) -> list:
        """解析 range() 表达式"""
        match = re.match(r"range\((\d+)\)", expr)
        if match:
            end = int(match.group(1))
            return list(range(end))

        match = re.match(r"range\((\d+),\s*(\d+)\)", expr)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            return list(range(start, end))

        raise ValueError(f"无效的 range 表达式: {expr}")

    def _evaluate_condition(self, condition_str: str) -> bool:
        """安全评估条件表达式"""
        def replace_var(match):
            ref = match.group(1)
            value = self._resolve_ref(ref)
            if value is None:
                return "None"
            if isinstance(value, str):
                return f'"{value}"'
            return str(value)

        pattern = r'\$\{([^}]+)\}'
        expr = re.sub(pattern, replace_var, condition_str)

        if not self._is_safe_expression(expr):
            logger.warning(f"条件表达式包含不安全内容: {expr}")
            return False

        allowed_names = {"True": True, "False": False, "None": None}
        try:
            result = eval(expr, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"条件评估失败: {condition_str}, {e}")
            return False

    def _is_safe_expression(self, expr: str) -> bool:
        """检查表达式是否安全"""
        try:
            tree = ast.parse(expr, mode="eval")

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    return False
                if isinstance(node, ast.Attribute):
                    if node.attr.startswith("_"):
                        return False
                if isinstance(node, ast.Name):
                    if node.id.startswith("_"):
                        return False
            return True
        except SyntaxError:
            return False


## lib/mail_manager.py
"""CiviBBS 邮件管理模块 - 基于文件系统的邮件协议实现"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class Mail:
    """一封邮件"""

    def __init__(self, data: Dict):
        self.mail_id = data.get("mail_id", "")
        self.thread_id = data.get("thread_id", "")
        self.in_reply_to = data.get("in_reply_to", "")
        self.fr = data.get("from", "")
        self.to = data.get("to", [])
        self.subject = data.get("subject", "")
        self.body = data.get("body", "")
        self.timestamp = data.get("timestamp", "")
        self.status = data.get("status", "new")

    def to_dict(self) -> Dict:
        return {
            "mail_id": self.mail_id,
            "thread_id": self.thread_id,
            "in_reply_to": self.in_reply_to,
            "from": self.fr,
            "to": self.to,
            "subject": self.subject,
            "body": self.body,
            "timestamp": self.timestamp,
            "status": self.status,
        }


class MailManager:
    """邮件管理器 - 负责邮件的创建、投递、读取、标记"""

    def __init__(self, mail_root: str):
        self.mail_root = Path(mail_root)
        self.agents_dir = self.mail_root / "agents"

    def _agent_dir(self, agent_id: str) -> Path:
        return self.agents_dir / agent_id

    def _inbox_dir(self, agent_id: str) -> Path:
        d = self._agent_dir(agent_id) / "inbox"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _outbox_dir(self, agent_id: str) -> Path:
        d = self._agent_dir(agent_id) / "outbox"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _new_mail_id(self) -> str:
        return f"mail_{uuid.uuid4().hex[:12]}"

    def _new_thread_id(self) -> str:
        return f"thread_{uuid.uuid4().hex[:12]}"

    def _now(self) -> str:
        return datetime.now().isoformat()

    def create_mail(self, *, fr: str, to: List[str], body: str,
                    subject: str = "", thread_id: str = "",
                    in_reply_to: str = "") -> Mail:
        """创建一封邮件"""
        mail_id = self._new_mail_id()
        if not thread_id:
            thread_id = self._new_thread_id()
        return Mail({
            "mail_id": mail_id,
            "thread_id": thread_id,
            "in_reply_to": in_reply_to,
            "from": fr,
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": self._now(),
            "status": "new",
        })

    def deliver(self, mail: Mail) -> None:
        """投递邮件：写入发件人outbox和所有收件人inbox"""
        data = mail.to_dict()

        # 写入发件人outbox
        outbox = self._outbox_dir(mail.fr)
        with open(outbox / f"{mail.mail_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 写入每个收件人inbox
        for recipient in mail.to:
            inbox = self._inbox_dir(recipient)
            with open(inbox / f"{mail.mail_id}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def read_mail(self, agent_id: str, mail_id: str) -> Optional[Mail]:
        """读取一封邮件（先查inbox，再查outbox）"""
        for folder in ("inbox", "outbox"):
            path = self._agent_dir(agent_id) / folder / f"{mail_id}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return Mail(json.load(f))
        return None

    def list_inbox(self, agent_id: str, status: str = None) -> List[Mail]:
        """列出收件箱邮件"""
        inbox = self._inbox_dir(agent_id)
        mails = []
        for path in sorted(inbox.glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                m = Mail(json.load(f))
                if status is None or m.status == status:
                    mails.append(m)
        return mails

    def list_outbox(self, agent_id: str) -> List[Mail]:
        """列出发件箱邮件"""
        outbox = self._outbox_dir(agent_id)
        mails = []
        for path in sorted(outbox.glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                mails.append(Mail(json.load(f)))
        return mails

    def load_thread(self, agent_id: str, thread_id: str) -> List[Mail]:
        """加载某个agent的某个thread下所有邮件（按时间排序）"""
        mails = []
        for path in self._inbox_dir(agent_id).glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                m = Mail(json.load(f))
                if m.thread_id == thread_id:
                    mails.append(m)
        for path in self._outbox_dir(agent_id).glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                m = Mail(json.load(f))
                if m.thread_id == thread_id:
                    mails.append(m)
        mails.sort(key=lambda m: m.timestamp)
        return mails

    def mark(self, agent_id: str, mail_id: str, status: str) -> None:
        """标记邮件状态（new/read/replied）"""
        for folder in ("inbox", "outbox"):
            path = self._agent_dir(agent_id) / folder / f"{mail_id}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["status"] = status
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return

    def get_or_create_thread(self, thread_id: str = "") -> str:
        """获取已有thread_id或创建新的"""
        return thread_id if thread_id else self._new_thread_id()


# 全局单例
_instance = None

def get_mail_manager(mail_root: str = None) -> MailManager:
    global _instance
    if _instance is None:
        if mail_root is None:
            raise ValueError("首次调用必须提供mail_root")
        _instance = MailManager(mail_root)
    return _instance


## lib/topology.py
"""CiviBBS 拓扑管理模块 - 智能体注册、心跳、拓扑存储"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TopologyManager:
    """拓扑管理器 - 负责智能体注册、心跳、拓扑存储读写"""

    def __init__(self, mail_root: str, topo_stores: List[str] = None, copies: int = 10):
        self.mail_root = Path(mail_root)
        self.copies = copies
        self.topo_stores = []
        default_stores = [self.mail_root / "topo_store_1", self.mail_root / "topo_store_2"]
        if topo_stores:
            for s in topo_stores:
                p = Path(s)
                self.topo_stores.append(p)
        else:
            self.topo_stores = default_stores
        self.agents_dir = self.mail_root / "agents"
        self._activity: Dict[str, dict] = {}

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _agent_inbox(self, agent_id: str) -> Path:
        return self.agents_dir / agent_id / "inbox"

    def register(self, agent_id: str, capabilities: List[str] = None, agent_type: str = "unknown") -> dict:
        """注册智能体到拓扑"""
        entry = {
            "agent_id": agent_id,
            "type": agent_type,
            "capabilities": capabilities or [],
            "inbox": str(self._agent_inbox(agent_id)),
            "last_seen": self._now(),
            "status": "alive",
        }
        self._activity[agent_id] = entry
        self._write_to_stores()
        return entry

    def heartbeat(self, agent_id: str) -> None:
        """更新智能体心跳"""
        if agent_id in self._activity:
            self._activity[agent_id]["last_seen"] = self._now()
            self._activity[agent_id]["status"] = "alive"

    def check_alive(self, timeout_minutes: int = 120) -> List[str]:
        """检查超时智能体，返回超时ID列表"""
        now = datetime.now()
        timed_out = []
        for aid, entry in self._activity.items():
            if entry["status"] != "alive":
                continue
            try:
                last = datetime.fromisoformat(entry["last_seen"])
                if (now - last).total_seconds() > timeout_minutes * 60:
                    entry["status"] = "suspect"
                    timed_out.append(aid)
            except (ValueError, TypeError):
                pass
        return timed_out

    def mark_dead(self, agent_id: str) -> None:
        """标记智能体为离线"""
        if agent_id in self._activity:
            self._activity[agent_id]["status"] = "dead"
            self._write_to_stores()

    def _write_to_stores(self) -> None:
        """写入所有拓扑存储（带副本）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        msg_id = uuid.uuid4().hex[:8]

        topo_data = {
            "timestamp": self._now(),
            "unit_id": "topo_manager",
            "agents": list(self._activity.values()),
            "agent_count": len(self._activity),
        }

        for store_path in self.topo_stores:
            inbox = store_path / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            for i in range(1, self.copies + 1):
                filename = f"topo_{timestamp}_{msg_id}.copy.{i}.json"
                filepath = inbox / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(topo_data, f, ensure_ascii=False, indent=2)

    def read_latest(self) -> Optional[dict]:
        """从拓扑存储读取最新拓扑（原子移动抢占一个副本）"""
        for store_path in self.topo_stores:
            inbox = store_path / "inbox"
            if not inbox.exists():
                continue
            files = sorted(inbox.glob("topo_*.copy.*.json"), reverse=True)
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        return json.load(fp)
                except (OSError, json.JSONDecodeError):
                    continue
        return None

    def get_topology(self) -> dict:
        """获取当前拓扑（优先内存，其次存储）"""
        if self._activity:
            return {
                "timestamp": self._now(),
                "agents": list(self._activity.values()),
                "agent_count": len(self._activity),
            }
        stored = self.read_latest()
        if stored:
            for a in stored.get("agents", []):
                self._activity[a["agent_id"]] = a
            return stored
        return {"timestamp": self._now(), "agents": [], "agent_count": 0}

    def scan_profiles(self) -> None:
        """扫描所有智能体profile并注册"""
        if not self.agents_dir.exists():
            return
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            profile_file = agent_dir / "profile.json"
            if profile_file.exists():
                try:
                    with open(profile_file, "r", encoding="utf-8") as f:
                        profile = json.load(f)
                    aid = agent_dir.name
                    if aid not in self._activity:
                        self.register(
                            agent_id=aid,
                            capabilities=profile.get("expertise", []),
                            agent_type=profile.get("type", "unknown"),
                        )
                    else:
                        self.heartbeat(aid)
                except Exception:
                    pass
        self._write_to_stores()


## lib/ai_model.py
"""
CiviBBS V2.0 - AI模型集成

支持多种AI模型：
1. 讯飞星火 (Spark 4.0 Ultra) - 默认
2. OpenAI API (GPT-4, GPT-3.5)
3. Anthropic API (Claude)
4. Ollama 本地模型
5. 简单模板回复（无API时的后备）
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AIModelBase(ABC):
    """AI模型基类"""

    @abstractmethod
    def generate(self, prompt: str, context: Dict = None) -> str:
        """生成回复"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查模型是否可用"""
        pass


class SparkModelAdapter(AIModelBase):
    """讯飞星火模型适配器"""

    def __init__(self, api_key: str = None, api_secret: str = None,
                 app_id: str = None, model: str = "spark-4.0-ultra"):
        self.api_key = api_key or os.environ.get("SPARK_API_KEY")
        self.api_secret = api_secret or os.environ.get("SPARK_API_SECRET")
        self.app_id = app_id or os.environ.get("SPARK_APP_ID")
        self.model = model
        self._spark = None

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_secret and self.app_id)

    def _get_spark(self):
        if self._spark is None and self.is_available():
            try:
                from spark_model import SparkModel
                self._spark = SparkModel(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    app_id=self.app_id,
                    model=self.model,
                )
            except ImportError:
                logger.warning("spark_model模块未找到")
        return self._spark

    def generate(self, prompt: str, context: Dict = None) -> str:
        spark = self._get_spark()
        if not spark:
            return None

        context = context or {}
        system_prompt = f"你是{context.get('name', 'AI助手')}，友好、专业、简洁。"
        if context.get('expertise'):
            system_prompt += f"你的专长是：{', '.join(context['expertise'])}。"

        return spark.simple_chat(prompt, system_prompt)


class OpenAIModel(AIModelBase):
    """OpenAI兼容模型（支持DeepSeek等）"""

    def __init__(self, api_key: str = None, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url
        self._client = None

    def is_available(self) -> bool:
        return self.api_key is not None

    def _get_client(self):
        if self._client is None and self.is_available():
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                logger.warning("openai包未安装")
        return self._client

    def generate(self, prompt: str, context: Dict = None) -> str:
        client = self._get_client()
        if not client:
            return None

        context = context or {}
        system_prompt = f"你是{context.get('name', 'AI助手')}，友好、专业、简洁。"
        if context.get('expertise'):
            system_prompt += f"你的专长是：{', '.join(context['expertise'])}。"
        if context.get('personality'):
            system_prompt += f"你的性格特点：{context['personality']}。"

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek调用失败: {e}")
            return None


class AnthropicModel(AIModelBase):
    """Anthropic Claude模型"""

    def __init__(self, api_key: str = None, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    def is_available(self) -> bool:
        return self.api_key is not None

    def _get_client(self):
        if self._client is None and self.is_available():
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic包未安装")
        return self._client

    def generate(self, prompt: str, context: Dict = None) -> str:
        client = self._get_client()
        if not client:
            return None

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic调用失败: {e}")
            return None


class OllamaModel(AIModelBase):
    """Ollama本地模型"""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama2"):
        self.host = host
        self.model = model

    def is_available(self) -> bool:
        try:
            import requests
            r = requests.get(f"{self.host}/api/tags", timeout=2)
            return r.status_code == 200
        except:
            return False

    def generate(self, prompt: str, context: Dict = None) -> str:
        try:
            import requests
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama调用失败: {e}")
        return None


class TemplateModel(AIModelBase):
    """模板模型（后备方案）"""

    def __init__(self, templates: Dict = None):
        self.templates = templates or self._default_templates()

    def _default_templates(self) -> Dict:
        return {
            "greeting": "你好！我是{name}，一个AI助手。有什么可以帮你的吗？",
            "python": "关于Python，我建议：\n1. 从基础语法开始\n2. 多做练习项目\n3. 阅读优秀代码",
            "help": "很高兴帮助你！请告诉我你遇到的具体问题。",
            "unknown": "收到！如果需要帮助，随时告诉我。"
        }

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, context: Dict = None) -> str:
        context = context or {}
        name = context.get("name", "AI助手")
        prompt_lower = prompt.lower()

        if "python" in prompt_lower:
            return self.templates["python"]
        elif "帮助" in prompt or "help" in prompt_lower:
            return self.templates["help"]
        elif "谁" in prompt and "在" in prompt:
            return f"我在！我是{name}。有什么可以帮你的吗？"
        else:
            return self.templates["unknown"]


class AIModelManager:
    """AI模型管理器"""

    def __init__(self):
        self.models: Dict[str, AIModelBase] = {}
        self.default_model = None
        self._init_models()

    def _init_models(self):
        """初始化模型"""
        cfg = self._load_config()

        # DeepSeek Chat
        deepseek_chat = OpenAIModel(
            api_key=cfg.get("deepseek", {}).get("api_key"),
            model="deepseek-chat",
            base_url=cfg.get("deepseek", {}).get("base_url", "https://api.deepseek.com"),
        )
        if deepseek_chat.is_available():
            self.models["deepseek-chat"] = deepseek_chat
            self.default_model = "deepseek-chat"
            logger.info("DeepSeek-Chat模型已加载")

        # DeepSeek Reasoner
        deepseek_reasoner = OpenAIModel(
            api_key=cfg.get("deepseek", {}).get("api_key"),
            model="deepseek-reasoner",
            base_url=cfg.get("deepseek", {}).get("base_url", "https://api.deepseek.com"),
        )
        if deepseek_reasoner.is_available():
            self.models["deepseek-reasoner"] = deepseek_reasoner
            if not self.default_model:
                self.default_model = "deepseek-reasoner"
            logger.info("DeepSeek-Reasoner模型已加载")

        # 讯飞星火
        spark = SparkModelAdapter(
            api_key=cfg.get("spark", {}).get("api_key"),
            api_secret=cfg.get("spark", {}).get("api_secret"),
            app_id=cfg.get("spark", {}).get("app_id"),
            model=cfg.get("spark", {}).get("model", "spark-4.0-ultra"),
        )
        if spark.is_available():
            self.models["spark"] = spark
            if not self.default_model:
                self.default_model = "spark"
            logger.info("讯飞星火模型已加载")

        # Anthropic Claude
        anthropic = AnthropicModel(
            api_key=cfg.get("anthropic", {}).get("api_key"),
            model=cfg.get("anthropic", {}).get("model", "claude-sonnet-4-6"),
        )
        if anthropic.is_available():
            self.models["anthropic"] = anthropic
            if not self.default_model:
                self.default_model = "anthropic"
            logger.info("Anthropic模型已加载")

        # Ollama本地模型
        ollama = OllamaModel(
            host=cfg.get("ollama", {}).get("host", "http://localhost:11434"),
            model=cfg.get("ollama", {}).get("model", "llama2"),
        )
        if ollama.is_available():
            self.models["ollama"] = ollama
            if not self.default_model:
                self.default_model = "ollama"
            logger.info("Ollama模型已加载")

        # 总是添加模板模型作为后备
        self.models["template"] = TemplateModel()
        if not self.default_model:
            self.default_model = "template"
            logger.info("使用模板模型")

    def _load_config(self) -> Dict:
        """从配置文件加载AI模型配置"""
        from pathlib import Path
        config_paths = [
            Path(__file__).parent.parent / "runtime" / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
        ]
        for cp in config_paths:
            if cp.exists():
                try:
                    import yaml
                    with open(cp, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    pass
        return {}

    def generate(
        self,
        prompt: str,
        context: Dict = None,
        model: str = None,
        fallback: bool = True
    ) -> str:
        """
        生成回复

        Args:
            prompt: 提示词
            context: 上下文
            model: 指定模型
            fallback: 是否使用后备模型

        Returns:
            生成的回复
        """
        model_name = model or self.default_model

        if model_name in self.models:
            result = self.models[model_name].generate(prompt, context)
            if result:
                return result

        # 尝试其他模型
        if fallback:
            for name, model_instance in self.models.items():
                if name != model_name and model_instance.is_available():
                    result = model_instance.generate(prompt, context)
                    if result:
                        return result

        # 最后使用模板
        return self.models["template"].generate(prompt, context)

    def register_model(self, name: str, model: AIModelBase):
        """注册模型"""
        self.models[name] = model

    def list_models(self) -> list:
        """列出可用模型"""
        return [
            {"name": name, "available": model.is_available()}
            for name, model in self.models.items()
        ]


# 全局模型管理器
_model_manager = None


def get_model_manager() -> AIModelManager:
    """获取全局模型管理器"""
    global _model_manager
    if _model_manager is None:
        _model_manager = AIModelManager()
    return _model_manager


def generate_reply(
    content: str,
    author: str,
    agent_name: str,
    expertise: list = None
) -> str:
    """
    生成AI回复的便捷函数

    Args:
        content: 用户消息内容
        author: 用户名
        agent_name: AI名称
        expertise: AI专长

    Returns:
        生成的回复
    """
    manager = get_model_manager()

    # 构建提示词
    prompt = f"""用户 {author} 说：{content}

请作为 {agent_name} 回复。{'你的专长是：' + ', '.join(expertise) if expertise else ''}

要求：
1. 友好、专业、简洁
2. 针对用户的问题给出有价值的回复
3. 如果是技术问题，给出具体建议
"""

    context = {
        "name": agent_name,
        "author": author,
        "expertise": expertise or []
    }

    return manager.generate(prompt, context)


## lib/spark_model.py
"""
CiviBBS V2.0 - 讯飞星火大模型接入

通过WebSocket协议调用讯飞星火API
支持模型: generalv3.5 (Spark4.0 Ultra), iflycode.ge (代码模型)
"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode, urlparse

import websocket

logger = logging.getLogger(__name__)

MODEL_MAP = {
    "spark-4.0-ultra": "wss://spark-api.xf-yun.com/v3.5/chat",
    "spark-3.5": "wss://spark-api.xf-yun.com/v3.1/chat",
    "spark-code": "wss://spark-api.xf-yun.com/v3.2/chat",
}

DOMAIN_MAP = {
    "spark-4.0-ultra": "generalv3.5",
    "spark-3.5": "generalv3",
    "spark-code": "iflycode.ge",
}

_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = datetime.datetime.utcfromtimestamp(timestamp).timetuple()[:7]
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )


def _create_url(api_key: str, api_secret: str, ws_url: str) -> str:
    """生成带鉴权参数的WebSocket URL"""
    url_obj = urlparse(ws_url)
    host = url_obj.netloc
    path = url_obj.path

    now = datetime.datetime.now()
    date = _format_date_time(now.timestamp())

    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature_sha).decode('utf-8')

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_b64}"'
    )
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

    params = {"authorization": authorization, "date": date, "host": host}
    return ws_url + '?' + urlencode(params)


class SparkModel:
    """讯飞星火大模型"""

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        app_id: str = None,
        model: str = "spark-4.0-ultra",
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.app_id = app_id
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_secret and self.app_id)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        调用星火大模型

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度
            max_tokens: 最大token数

        Returns:
            模型回复文本
        """
        if not self.is_available():
            return None

        ws_url = MODEL_MAP.get(self.model, MODEL_MAP["spark-4.0-ultra"])
        domain = DOMAIN_MAP.get(self.model, "generalv3.5")
        url = _create_url(self.api_key, self.api_secret, ws_url)

        send_data = {
            "header": {"app_id": self.app_id},
            "parameter": {
                "chat": {
                    "domain": domain,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens or self.max_tokens,
                }
            },
            "payload": {
                "message": {
                    "text": messages
                }
            }
        }

        try:
            ws = websocket.create_connection(url)
            ws.send(json.dumps(send_data, ensure_ascii=False))

            result = ""
            while True:
                data = ws.recv()
                if not data:
                    break
                msg = json.loads(data)

                code = msg.get("header", {}).get("code", -1)
                if code != 0:
                    error_msg = msg.get("header", {}).get("message", "unknown error")
                    logger.error(f"星火API错误: code={code}, msg={error_msg}")
                    ws.close()
                    return None

                choices = msg.get("payload", {}).get("choices", {})
                texts = choices.get("text", [])
                if texts:
                    result += texts[0].get("content", "")

                status = msg.get("header", {}).get("status", 0)
                if status == 2:
                    break

            ws.close()
            return result

        except Exception as e:
            logger.error(f"星火API调用失败: {e}")
            return None

    def simple_chat(self, prompt: str, system_prompt: str = None) -> str:
        """
        简单对话接口

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词

        Returns:
            模型回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)


# 全局实例
_spark_model: Optional[SparkModel] = None


def _load_config() -> Dict[str, str]:
    """从配置文件加载星火API配置"""
    import yaml
    from pathlib import Path

    config_paths = [
        Path(__file__).parent.parent / "runtime" / "config.yaml",
        Path(__file__).parent.parent / "config.yaml",
    ]
    for cp in config_paths:
        if cp.exists():
            with open(cp, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            spark_cfg = cfg.get("spark", {})
            if spark_cfg:
                return spark_cfg
    return {}


def get_spark_model(
    api_key: str = None,
    api_secret: str = None,
    app_id: str = None,
    model: str = None,
) -> SparkModel:
    """获取全局星火模型实例"""
    global _spark_model
    if _spark_model is None:
        import os
        cfg = _load_config()
        _spark_model = SparkModel(
            api_key=api_key or os.environ.get("SPARK_API_KEY") or cfg.get("api_key"),
            api_secret=api_secret or os.environ.get("SPARK_API_SECRET") or cfg.get("api_secret"),
            app_id=app_id or os.environ.get("SPARK_APP_ID") or cfg.get("app_id"),
            model=model or os.environ.get("SPARK_MODEL") or cfg.get("model", "spark-4.0-ultra"),
        )
    return _spark_model


def chat_with_spark(
    prompt: str,
    system_prompt: str = "你是CiviBBS的AI助手，友好、专业、简洁。",
    model: str = None,
) -> str:
    """
    与星火对话的便捷函数

    Args:
        prompt: 用户消息
        system_prompt: 系统提示词
        model: 模型名称

    Returns:
        AI回复
    """
    spark = get_spark_model(model=model)
    return spark.simple_chat(prompt, system_prompt)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("用法: python spark_model.py <api_key> <api_secret> <app_id>")
        sys.exit(1)

    m = SparkModel(
        api_key=sys.argv[1],
        api_secret=sys.argv[2],
        app_id=sys.argv[3],
    )
    print(f"模型可用: {m.is_available()}")

    reply = m.simple_chat("你好，请介绍一下你自己")
    print(f"回复: {reply}")


## web/app.py
"""
CiviBBS V2.0 - Flask Web Application

BBS Web 服务，提供：
- 讨论列表
- 帖子查看
- 用户交互
"""
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

logger = logging.getLogger(__name__)


def create_app(config: Dict = None) -> Flask:
    """
    创建 Flask 应用

    Args:
        config: 配置字典

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)
    app.secret_key = config.get("secret_key", "civibbs_secret_key_2026")

    # 配置
    app.config["MAIL_ROOT"] = config.get("mail_root", "./data/mail")
    app.config["DATA_DIR"] = config.get("data_dir", "./data/app")
    app.config["BBS_DATA_DIR"] = Path(config.get("data_dir", "./data/app")) / "bbs"

    # 确保目录存在
    Path(app.config["BBS_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["MAIL_ROOT"]).mkdir(parents=True, exist_ok=True)

    # 注册路由
    register_routes(app)

    # 注册 API
    register_api(app)

    return app


def register_routes(app: Flask):
    """注册页面路由"""

    @app.route("/")
    def index():
        """首页 - 讨论列表"""
        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        index_file = bbs_dir / "index.json"

        discussions = []
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                discussions = json.load(f)

        return render_template("index.html", discussions=discussions)

    @app.route("/discussion/<discussion_id>")
    def discussion(discussion_id: str):
        """讨论详情页"""
        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        discussion_file = bbs_dir / "discussions" / f"{discussion_id}.json"

        if not discussion_file.exists():
            return "讨论不存在", 404

        with open(discussion_file, "r", encoding="utf-8") as f:
            discussion_data = json.load(f)

        return render_template("discussion.html", discussion=discussion_data)

    @app.route("/new")
    def new_discussion():
        """创建新讨论"""
        return render_template("new_discussion.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """登录页面"""
        if request.method == "POST":
            username = request.form.get("username")
            if username:
                session["user"] = username
                return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        """登出"""
        session.pop("user", None)
        return redirect(url_for("index"))

    @app.route("/health")
    def health():
        """健康检查"""
        return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

    @app.route("/chat")
    def chat():
        """AI聊天页面"""
        return render_template("chat.html")

    @app.route("/topo")
    def topo():
        """拓扑图页面"""
        return render_template("topo.html")

    @app.route("/feishu/webhook", methods=["POST"])
    def feishu_webhook():
        """飞书Webhook"""
        import sys
        base_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(base_dir / "adapters"))

        body = request.get_data(as_text=True)
        event = json.loads(body)

        # URL验证
        if event.get("type") == "url_verification":
            return jsonify({"challenge": event.get("challenge")})

        # 处理消息
        if event.get("type") == "event_callback":
            event_data = event.get("event", {})
            if event_data.get("type") == "message":
                # 获取消息内容
                message = event_data.get("message", {})
                content = json.loads(message.get("content", "{}"))
                text = content.get("text", "")
                chat_id = message.get("chat_id", "")

                # 调用AI回复
                if text:
                    sys.path.insert(0, str(base_dir / "lib"))
                    from ai_model import get_model_manager

                    manager = get_model_manager()
                    reply = manager.generate(text, context={"name": "AI助手"})

                    # 发送回复（需要飞书token）
                    return jsonify({"code": 0, "reply": reply})

        return jsonify({"code": 0})


def register_api(app: Flask):
    """注册 API 路由"""

    @app.route("/api/discussions", methods=["GET"])
    def api_list_discussions():
        """获取讨论列表"""
        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        index_file = bbs_dir / "index.json"

        discussions = []
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                discussions = json.load(f)

        return jsonify({"discussions": discussions})

    @app.route("/api/discussions", methods=["POST"])
    def api_create_discussion():
        """创建新讨论"""
        data = request.get_json()
        title = data.get("title")
        content = data.get("content")
        author = session.get("user", data.get("author", "anonymous"))

        if not title or not content:
            return jsonify({"error": "标题和内容不能为空"}), 400

        discussion_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        discussion_data = {
            "id": discussion_id,
            "title": title,
            "author": author,
            "created_at": now,
            "updated_at": now,
            "posts": [
                {
                    "id": str(uuid.uuid4())[:8],
                    "author": author,
                    "content": content,
                    "created_at": now
                }
            ]
        }

        # 保存讨论
        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        discussions_dir = bbs_dir / "discussions"
        discussions_dir.mkdir(parents=True, exist_ok=True)

        discussion_file = discussions_dir / f"{discussion_id}.json"
        with open(discussion_file, "w", encoding="utf-8") as f:
            json.dump(discussion_data, f, indent=2, ensure_ascii=False)

        # 更新索引
        index_file = bbs_dir / "index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = []

        index.insert(0, {
            "id": discussion_id,
            "title": title,
            "author": author,
            "created_at": now,
            "post_count": 1
        })

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        # 发送邮件通知
        _send_discussion_mail(app, discussion_data, "create")

        return jsonify({"success": True, "discussion_id": discussion_id})

    @app.route("/api/discussions/<discussion_id>/posts", methods=["POST"])
    def api_create_post(discussion_id: str):
        """添加帖子"""
        data = request.get_json()
        content = data.get("content")
        author = session.get("user", data.get("author", "anonymous"))

        if not content:
            return jsonify({"error": "内容不能为空"}), 400

        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        discussion_file = bbs_dir / "discussions" / f"{discussion_id}.json"

        if not discussion_file.exists():
            return jsonify({"error": "讨论不存在"}), 404

        with open(discussion_file, "r", encoding="utf-8") as f:
            discussion_data = json.load(f)

        now = datetime.now().isoformat()
        post = {
            "id": str(uuid.uuid4())[:8],
            "author": author,
            "content": content,
            "created_at": now
        }

        discussion_data["posts"].append(post)
        discussion_data["updated_at"] = now

        with open(discussion_file, "w", encoding="utf-8") as f:
            json.dump(discussion_data, f, indent=2, ensure_ascii=False)

        # 更新索引中的帖子数
        _update_index_post_count(bbs_dir, discussion_id, len(discussion_data["posts"]))

        # 发送邮件通知
        _send_post_mail(app, discussion_data, post)

        return jsonify({"success": True, "post_id": post["id"]})

    @app.route("/api/discussions/<discussion_id>", methods=["GET"])
    def api_get_discussion(discussion_id: str):
        """获取讨论详情"""
        bbs_dir = Path(app.config["BBS_DATA_DIR"])
        discussion_file = bbs_dir / "discussions" / f"{discussion_id}.json"

        if not discussion_file.exists():
            return jsonify({"error": "讨论不存在"}), 404

        with open(discussion_file, "r", encoding="utf-8") as f:
            discussion_data = json.load(f)

        return jsonify(discussion_data)

    @app.route("/api/agents", methods=["GET"])
    def api_list_agents():
        """获取活跃智能体列表（含profile信息）"""
        mail_root = Path(app.config["MAIL_ROOT"])
        agents_dir = mail_root / "agents"

        agents = []
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if agent_dir.is_dir():
                    inbox = agent_dir / "inbox"
                    mail_count = len(list(inbox.glob("*.json"))) if inbox.exists() else 0

                    profile_file = agent_dir / "profile.json"
                    profile = {}
                    if profile_file.exists():
                        try:
                            with open(profile_file, "r", encoding="utf-8") as f:
                                profile = json.load(f)
                        except Exception:
                            pass

                    agents.append({
                        "id": agent_dir.name,
                        "name": profile.get("name", agent_dir.name),
                        "type": profile.get("type", "unknown"),
                        "icon": profile.get("icon", "👤"),
                        "expertise": profile.get("expertise", []),
                        "description": profile.get("description", ""),
                        "model": profile.get("model", ""),
                        "personality": profile.get("personality", ""),
                        "status": profile.get("status", "offline"),
                        "mail_count": mail_count,
                    })

        return jsonify({"agents": agents})

    @app.route("/api/tasks", methods=["POST"])
    def api_submit_task():
        """提交任务"""
        data = request.get_json()
        task_type = data.get("task_type")
        content = data.get("content")
        target_agent = data.get("target_agent", "ac_001")

        if not task_type or not content:
            return jsonify({"error": "任务类型和内容不能为空"}), 400

        task_id = _submit_task(app, task_type, content, target_agent)

        return jsonify({"success": True, "task_id": task_id})

    @app.route("/api/topo", methods=["GET"])
    def api_get_topology():
        """获取当前拓扑"""
        import sys as _sys
        _base_dir = Path(__file__).parent.parent
        _sys.path.insert(0, str(_base_dir / "lib"))
        from topology import TopologyManager
        _topo_mgr = TopologyManager(str(Path(app.config["MAIL_ROOT"])))
        _topo_mgr.scan_profiles()
        return jsonify(_topo_mgr.get_topology())

    @app.route("/api/topo/refresh", methods=["POST"])
    def api_refresh_topology():
        """刷新拓扑"""
        import sys as _sys
        _base_dir = Path(__file__).parent.parent
        _sys.path.insert(0, str(_base_dir / "lib"))
        from topology import TopologyManager
        _topo_mgr = TopologyManager(str(Path(app.config["MAIL_ROOT"])))
        _topo_mgr._activity = {}
        _topo_mgr.scan_profiles()
        _topo = _topo_mgr.get_topology()
        return jsonify({"success": True, "agent_count": _topo["agent_count"]})

    def _load_ai_agents():
        """从profile.json动态加载AI智能体"""
        mail_root = Path(app.config["MAIL_ROOT"])
        agents_dir = mail_root / "agents"
        agents = {}
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                profile_file = agent_dir / "profile.json"
                if profile_file.exists():
                    try:
                        with open(profile_file, "r", encoding="utf-8") as f:
                            profile = json.load(f)
                        agents[agent_dir.name] = {
                            "name": profile.get("name", agent_dir.name),
                            "type": profile.get("type", "unknown"),
                            "expertise": profile.get("expertise", []),
                            "description": profile.get("description", ""),
                            "icon": profile.get("icon", "🤖"),
                            "model": profile.get("model", ""),
                            "personality": profile.get("personality", ""),
                        }
                    except Exception:
                        pass
        if not agents:
            agents["ai_agent_001"] = {"name": "AI助手", "expertise": [], "description": "", "icon": "🤖", "model": "", "type": "ai", "personality": ""}
        return agents

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """AI聊天API - 邮件驱动，支持单聊/群聊/讨论三种模式"""
        data = request.get_json()
        agent_id = data.get("agent_id", "ai_agent_001")
        message = data.get("message", "")
        mode = data.get("mode", "single")
        thread_id = data.get("thread_id", "")
        sender_id = data.get("sender_id", "human_user")

        if not message:
            return jsonify({"error": "消息不能为空"}), 400

        agents = _load_ai_agents()
        ai_agents = {k: v for k, v in agents.items() if v.get("type") == "ai"}

        try:
            import sys
            from concurrent.futures import ThreadPoolExecutor, as_completed
            base_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(base_dir / "lib"))
            from ai_model import get_model_manager
            from mail_manager import MailManager

            mail_mgr = MailManager(str(Path(app.config["MAIL_ROOT"])))
            model_mgr = get_model_manager()

            # 1. 用户发消息 = 发邮件
            thread_id = mail_mgr.get_or_create_thread(thread_id)
            recipients = [agent_id] if mode == "single" else list(ai_agents.keys())
            user_mail = mail_mgr.create_mail(
                fr=sender_id, to=recipients, body=message,
                subject=f"Chat [{mode}]", thread_id=thread_id,
            )
            mail_mgr.deliver(user_mail)

            def _generate_for_agent(aid, agent_info, prompt):
                model_name = agent_info.get("model", "")
                return model_mgr.generate(
                    prompt=prompt,
                    context={"name": agent_info["name"], "expertise": agent_info["expertise"], "personality": agent_info.get("personality", "")},
                    model=model_name or None,
                )

            def _load_context(aid, tid):
                """从邮件历史构建上下文"""
                thread_mails = mail_mgr.load_thread(aid, tid)
                if not thread_mails:
                    return []
                ctx = []
                for m in thread_mails:
                    if m.fr == aid:
                        ctx.append({"role": "assistant", "content": m.body})
                    else:
                        ctx.append({"role": "user", "content": f"{m.fr}说：{m.body}"})
                return ctx

            # 2. AI回复 = 回邮件
            replies = []

            if mode == "single":
                aid = agent_id
                info = ai_agents.get(aid, next(iter(ai_agents.values())))
                ctx = _load_context(aid, thread_id)
                prompt = _build_prompt_from_context(message, ctx, info)
                reply_text = _generate_for_agent(aid, info, prompt) or "抱歉，我暂时无法回复。"
                reply_mail = mail_mgr.create_mail(
                    fr=aid, to=[sender_id], body=reply_text,
                    thread_id=thread_id, in_reply_to=user_mail.mail_id,
                )
                mail_mgr.deliver(reply_mail)
                mail_mgr.mark(aid, user_mail.mail_id, "replied")
                replies.append({"agent": info["name"], "reply": reply_text, "mail_id": reply_mail.mail_id})

            elif mode == "group":
                with ThreadPoolExecutor(max_workers=len(ai_agents)) as executor:
                    futures = {}
                    for aid, info in ai_agents.items():
                        ctx = _load_context(aid, thread_id)
                        prompt = _build_prompt_from_context(message, ctx, info)
                        future = executor.submit(_generate_for_agent, aid, info, prompt)
                        futures[future] = (aid, info)

                    for future in as_completed(futures):
                        aid, info = futures[future]
                        try:
                            reply_text = future.result() or "抱歉，我暂时无法回复。"
                        except Exception:
                            reply_text = "回复生成失败。"
                        reply_mail = mail_mgr.create_mail(
                            fr=aid, to=[sender_id], body=reply_text,
                            thread_id=thread_id, in_reply_to=user_mail.mail_id,
                        )
                        mail_mgr.deliver(reply_mail)
                        mail_mgr.mark(aid, user_mail.mail_id, "replied")
                        replies.append({"agent": info["name"], "reply": reply_text, "mail_id": reply_mail.mail_id})

            elif mode == "discussion":
                prev_mails = []
                for aid, info in ai_agents.items():
                    ctx = _load_context(aid, thread_id)
                    prompt = _build_discussion_prompt_from_context(message, info, ctx, prev_mails, agents)
                    reply_text = _generate_for_agent(aid, info, prompt) or "抱歉，我暂时无法回复。"
                    reply_to = prev_mails[-1].mail_id if prev_mails else user_mail.mail_id
                    reply_mail = mail_mgr.create_mail(
                        fr=aid, to=[sender_id], body=reply_text,
                        thread_id=thread_id, in_reply_to=reply_to,
                    )
                    mail_mgr.deliver(reply_mail)
                    mail_mgr.mark(aid, user_mail.mail_id, "replied")
                    prev_mails.append(reply_mail)
                    replies.append({"agent": info["name"], "reply": reply_text, "mail_id": reply_mail.mail_id})

            else:
                return jsonify({"error": f"未知模式: {mode}"}), 400

            return jsonify({
                "mode": mode,
                "thread_id": thread_id,
                "user_mail_id": user_mail.mail_id,
                "replies": replies,
            })

        except Exception as e:
            logger.error(f"AI对话错误: {e}")
            return jsonify({"error": f"错误: {str(e)}"})

    def _build_prompt_from_context(message, context, agent_info):
        """从邮件上下文构建prompt"""
        parts = []
        if context:
            parts.append("对话历史：")
            for c in context[-10:]:
                parts.append(f"  {c['content']}")
            parts.append("")
        parts.append(f"用户说：{message}")
        parts.append(f"请作为 {agent_info['name']} 回复。你的专长是：{', '.join(agent_info['expertise'])}。友好、专业、简洁。")
        return "\n".join(parts)

    def _build_discussion_prompt_from_context(message, agent_info, context, prev_mails, all_agents):
        """从邮件上下文+前序回复构建讨论prompt"""
        parts = []
        if context:
            parts.append("对话历史：")
            for c in context[-10:]:
                parts.append(f"  {c['content']}")
            parts.append("")
        parts.append(f"用户提出了一个话题：{message}")
        if prev_mails:
            parts.append("其他AI的观点：")
            for pm in prev_mails:
                sender_name = all_agents.get(pm.fr, {}).get("name", pm.fr)
                parts.append(f"  {sender_name}：{pm.body}")
            parts.append(f"请作为 {agent_info['name']} 补充你的观点，可以引用或点评其他AI的看法。你的专长是：{', '.join(agent_info['expertise'])}。")
        else:
            parts.append(f"请作为 {agent_info['name']} 先发表你的观点。你的专长是：{', '.join(agent_info['expertise'])}。友好、专业、简洁。")
        return "\n".join(parts)


def _send_discussion_mail(app: Flask, discussion: Dict, action: str):
    """发送讨论邮件通知"""
    mail_root = Path(app.config["MAIL_ROOT"])
    public_inbox = mail_root / "public" / "inbox"
    public_inbox.mkdir(parents=True, exist_ok=True)

    # 获取第一个帖子内容
    first_post = discussion.get("posts", [{}])[0].get("content", "")

    mail = {
        "msg_id": str(uuid.uuid4()),
        "from": "bbs_web",
        "to": "public",
        "type": "bbs_discussion",
        "content": {
            "action": action,
            "discussion_id": discussion["id"],
            "title": discussion["title"],
            "author": discussion["author"],
            "first_post": first_post
        },
        "timestamp": datetime.now().isoformat()
    }

    mail_file = public_inbox / f"discussion_{discussion['id']}.json"
    with open(mail_file, "w", encoding="utf-8") as f:
        json.dump(mail, f, indent=2, ensure_ascii=False)


def _send_post_mail(app: Flask, discussion: Dict, post: Dict):
    """发送帖子邮件通知"""
    mail_root = Path(app.config["MAIL_ROOT"])
    public_inbox = mail_root / "public" / "inbox"
    public_inbox.mkdir(parents=True, exist_ok=True)

    mail = {
        "msg_id": str(uuid.uuid4()),
        "from": "bbs_web",
        "to": "public",
        "type": "bbs_post",
        "content": {
            "discussion_id": discussion["id"],
            "post_id": post["id"],
            "author": post["author"],
            "content": post["content"][:200]  # 截取前200字符
        },
        "timestamp": datetime.now().isoformat()
    }

    mail_file = public_inbox / f"post_{post['id']}.json"
    with open(mail_file, "w", encoding="utf-8") as f:
        json.dump(mail, f, indent=2, ensure_ascii=False)


def _update_index_post_count(bbs_dir: Path, discussion_id: str, count: int):
    """更新索引中的帖子数"""
    index_file = bbs_dir / "index.json"
    if not index_file.exists():
        return

    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)

    for item in index:
        if item["id"] == discussion_id:
            item["post_count"] = count
            break

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _submit_task(app: Flask, task_type: str, content: Dict, target_agent: str) -> str:
    """提交任务到智能体"""
    mail_root = Path(app.config["MAIL_ROOT"])
    target_inbox = mail_root / "agents" / target_agent / "inbox"
    target_inbox.mkdir(parents=True, exist_ok=True)

    task_id = str(uuid.uuid4())
    mail = {
        "msg_id": task_id,
        "from": "bbs_web",
        "to": target_agent,
        "type": "task",
        "content": content,
        "context": {"task_type": task_type},
        "timestamp": datetime.now().isoformat()
    }

    mail_file = target_inbox / f"task_{task_id}.json"
    with open(mail_file, "w", encoding="utf-8") as f:
        json.dump(mail, f, indent=2, ensure_ascii=False)

    return task_id


class FlaskServer:
    """Flask 服务器管理类"""

    def __init__(self, config: Dict = None):
        """
        初始化服务器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.app = create_app(self.config)
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self, host: str = "0.0.0.0", port: int = 3006):
        """
        启动服务器

        Args:
            host: 监听地址
            port: 监听端口
        """
        self.running = True
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        self.server_thread.start()
        logger.info(f"Flask 服务器已启动: http://{host}:{port}")

    def stop(self):
        """停止服务器"""
        self.running = False
        logger.info("Flask 服务器已停止")


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="CiviBBS Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=3006, help="监听端口")
    parser.add_argument("--mail-root", default="./data/mail", help="邮件根目录")
    parser.add_argument("--data-dir", default="./data/app", help="应用数据目录")

    args = parser.parse_args()

    config = {
        "mail_root": args.mail_root,
        "data_dir": args.data_dir
    }

    server = FlaskServer(config)
    server.start(host=args.host, port=args.port)

    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()


## scheduler/ac_scheduler.py
"""
CiviBBS V2.0 - AC调度器（完整版）

AC (Agent Coordinator) 负责：
1. 接收用户任务
2. 拆解任务
3. 分配给合适的智能体
4. 监控任务进度
5. 超时重发
"""
import sys
import os
import json
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("ACScheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s"
)


class ACScheduler:
    """AC调度器"""

    def __init__(
        self,
        scheduler_id: str,
        mail_root: str,
        data_dir: str,
        topo_stores: List[str],
        task_timeout: int = 3600
    ):
        self.scheduler_id = scheduler_id
        self.mail_root = Path(mail_root)
        self.data_dir = Path(data_dir)
        self.topo_stores = [Path(p) for p in topo_stores]
        self.task_timeout = task_timeout

        # 收件箱
        self.inbox = self.mail_root / "agents" / scheduler_id / "inbox"
        self.processing = self.mail_root / "agents" / scheduler_id / "processing"

        # 任务存储
        self.task_store = self.data_dir / "ac" / "tasks.json"
        self.task_store.parent.mkdir(parents=True, exist_ok=True)

        # 任务表
        self.tasks: Dict[str, Dict] = {}

        # 智能体列表（从拓扑存储获取）
        self.agents: Dict[str, Dict] = {}

        # 运行状态
        self.running = False

        # 确保目录存在
        self._ensure_dirs()

        # 加载任务
        self._load_tasks()

    def _ensure_dirs(self):
        """确保目录存在"""
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.processing.mkdir(parents=True, exist_ok=True)

    def _load_tasks(self):
        """加载任务"""
        if self.task_store.exists():
            try:
                with open(self.task_store, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                logger.info(f"加载了 {len(self.tasks)} 个任务")
            except:
                self.tasks = {}

    def _save_tasks(self):
        """保存任务"""
        with open(self.task_store, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)

    def start(self):
        """启动调度器"""
        self.running = True
        logger.info(f"AC调度器启动: {self.scheduler_id}")

        # 启动线程
        threads = [
            threading.Thread(target=self._main_loop, daemon=True),
            threading.Thread(target=self._topology_loop, daemon=True),
            threading.Thread(target=self._timeout_check_loop, daemon=True),
        ]

        for t in threads:
            t.start()

        logger.info("AC调度器就绪")

    def stop(self):
        """停止"""
        self.running = False
        self._save_tasks()
        logger.info(f"AC调度器停止: {self.scheduler_id}")

    def _main_loop(self):
        """主循环"""
        while self.running:
            try:
                mail = self._take_mail()
                if mail:
                    self._process_mail(mail)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"主循环错误: {e}")
                time.sleep(1)

    def _topology_loop(self):
        """拓扑轮询"""
        while self.running:
            try:
                self._fetch_topology()
            except Exception as e:
                logger.error(f"拓扑轮询错误: {e}")
            time.sleep(1800)  # 30分钟

    def _timeout_check_loop(self):
        """超时检测"""
        while self.running:
            try:
                self._check_task_timeouts()
            except Exception as e:
                logger.error(f"超时检测错误: {e}")
            time.sleep(60)  # 1分钟

    def _take_mail(self):
        """取邮件"""
        for mail_file in list(self.inbox.glob("*.json")):
            try:
                processing_file = self.processing / mail_file.name
                os.rename(str(mail_file), str(processing_file))
                with open(processing_file, "r", encoding="utf-8") as f:
                    mail = json.load(f)
                os.remove(processing_file)
                return mail
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        return None

    def _process_mail(self, mail):
        """处理邮件"""
        mail_type = mail.get("type", "")
        sender = mail.get("from", "")

        logger.info(f"收到邮件: type={mail_type}, from={sender}")

        if mail_type == "task":
            self._handle_new_task(mail)
        elif mail_type == "result":
            self._handle_task_result(mail)
        elif mail_type == "progress":
            self._handle_task_progress(mail)
        elif mail_type == "shutdown":
            self.running = False

    def _handle_new_task(self, mail):
        """处理新任务"""
        content = mail.get("content", {})
        context = mail.get("context", {})
        task_type = context.get("task_type", "general")

        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        task = {
            "task_id": task_id,
            "type": task_type,
            "content": content,
            "context": context,
            "from": mail.get("from", "user"),
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "assigned_to": None,
            "attempts": 0
        }

        self.tasks[task_id] = task
        self._save_tasks()

        logger.info(f"新任务: {task_id} ({task_type})")

        # 分配任务
        self._assign_task(task_id)

    def _assign_task(self, task_id: str):
        """分配任务"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task_type = task.get("type", "general")

        # 查找合适的智能体
        agent_id = self._find_agent_for_task(task_type)

        if not agent_id:
            logger.warning(f"没有可用的智能体处理任务: {task_id}")
            task["status"] = "no_agent"
            self._save_tasks()
            return

        # 发送任务邮件
        self._send_task_mail(task, agent_id)

        # 更新任务状态
        task["status"] = "assigned"
        task["assigned_to"] = agent_id
        task["attempts"] += 1
        task["updated_at"] = datetime.now().isoformat()
        self._save_tasks()

        logger.info(f"任务 {task_id} 已分配给 {agent_id}")

    def _find_agent_for_task(self, task_type: str) -> Optional[str]:
        """查找合适的智能体"""
        candidates = []

        for agent_id, info in self.agents.items():
            capabilities = info.get("capabilities", [])
            status = info.get("status", "unknown")

            if status != "alive":
                continue

            # 检查能力匹配
            if task_type in capabilities or "general" in capabilities:
                candidates.append(agent_id)

        if not candidates:
            # 返回任意一个活跃的智能体
            for agent_id, info in self.agents.items():
                if info.get("status") == "alive" and agent_id.startswith("ai_agent"):
                    return agent_id
            return None

        # 简单轮询选择
        return candidates[0]

    def _send_task_mail(self, task: Dict, agent_id: str):
        """发送任务邮件"""
        agent_info = self.agents.get(agent_id, {})
        inbox = agent_info.get("inbox", "")

        if not inbox:
            inbox = self.mail_root / "agents" / agent_id / "inbox"

        inbox_path = Path(inbox)
        inbox_path.mkdir(parents=True, exist_ok=True)

        mail = {
            "msg_id": task["task_id"],
            "from": self.scheduler_id,
            "to": agent_id,
            "type": "task",
            "content": task["content"],
            "context": task["context"],
            "timestamp": datetime.now().isoformat()
        }

        mail_file = inbox_path / f"task_{task['task_id'][:8]}.json"
        with open(mail_file, "w", encoding="utf-8") as f:
            json.dump(mail, f, indent=2, ensure_ascii=False)

        logger.debug(f"任务邮件已发送: {task['task_id'][:8]} -> {agent_id}")

    def _handle_task_result(self, mail):
        """处理任务结果"""
        task_id = mail.get("in_reply_to") or mail.get("thread_id")
        result = mail.get("content", {})

        if task_id not in self.tasks:
            logger.warning(f"未知任务结果: {task_id}")
            return

        task = self.tasks[task_id]
        task["status"] = "completed"
        task["result"] = result
        task["updated_at"] = datetime.now().isoformat()
        self._save_tasks()

        logger.info(f"任务完成: {task_id}")

    def _handle_task_progress(self, mail):
        """处理任务进度"""
        task_id = mail.get("in_reply_to") or mail.get("thread_id")
        progress = mail.get("content", {})

        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task["progress"] = progress
        task["updated_at"] = datetime.now().isoformat()
        self._save_tasks()

        logger.debug(f"任务进度: {task_id}")

    def _fetch_topology(self):
        """获取拓扑"""
        for store_path in self.topo_stores:
            if not store_path.exists():
                continue

            files = sorted(
                store_path.glob("topo_*.copy.*.json"),
                key=lambda f: f.name,
                reverse=True
            )

            for f in files:
                try:
                    temp = f.with_suffix(".processing")
                    os.rename(str(f), str(temp))
                    with open(temp, "r", encoding="utf-8") as fp:
                        topo = json.load(fp)
                    os.remove(temp)

                    agents = topo.get("agents", [])
                    self.agents = {}
                    for agent_info in agents:
                        agent_id = agent_info.get("agent_id")
                        if agent_id:
                            self.agents[agent_id] = agent_info

                    logger.info(f"拓扑更新: {len(self.agents)} 个智能体")
                    return
                except (OSError, json.JSONDecodeError):
                    continue

    def _check_task_timeouts(self):
        """检查任务超时"""
        now = datetime.now()
        tasks_to_retry = []

        for task_id, task in list(self.tasks.items()):
            if task["status"] in ["completed", "cancelled"]:
                continue

            created_at = datetime.fromisoformat(task["created_at"])
            elapsed = (now - created_at).total_seconds()

            if elapsed > self.task_timeout:
                attempts = task.get("attempts", 0)
                if attempts < 3:
                    tasks_to_retry.append(task_id)
                else:
                    task["status"] = "timeout"
                    task["updated_at"] = now.isoformat()
                    logger.warning(f"任务超时: {task_id}")

        for task_id in tasks_to_retry:
            logger.info(f"重试任务: {task_id}")
            self._assign_task(task_id)

        if tasks_to_retry:
            self._save_tasks()

    def submit_task(self, task_type: str, content: Dict, context: Dict = None) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        task = {
            "task_id": task_id,
            "type": task_type,
            "content": content,
            "context": context or {},
            "from": "user",
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "assigned_to": None,
            "attempts": 0
        }

        self.tasks[task_id] = task
        self._save_tasks()
        self._assign_task(task_id)

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict:
        """获取所有任务"""
        return dict(self.tasks)

    def get_agents(self) -> Dict:
        """获取智能体列表"""
        return dict(self.agents)


def main():
    """入口"""
    import argparse

    parser = argparse.ArgumentParser(description="CiviBBS AC调度器")
    parser.add_argument("--id", default="ac_001", help="调度器ID")
    parser.add_argument("--mail-root", required=True, help="邮件根目录")
    parser.add_argument("--data-dir", required=True, help="数据目录")
    parser.add_argument("--topo-stores", required=True, help="拓扑存储")

    args = parser.parse_args()

    scheduler = ACScheduler(
        scheduler_id=args.id,
        mail_root=args.mail_root,
        data_dir=args.data_dir,
        topo_stores=args.topo_stores.split(",")
    )

    scheduler.start()

    try:
        while scheduler.running:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    main()


