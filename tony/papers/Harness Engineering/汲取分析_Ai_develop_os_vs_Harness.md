# Ai_develop_os_exc 能从 Harness Engineering 汲取什么

> 基于《Harness Engineering的本质是什么？》一文，与 Ai_develop_os_exc 项目的对比分析。
> 分析日期：2026-05-08

---

## 核心判断

**Ai_develop_os_exc 比 StateKanban 更接近 Harness Engineering 的"先天长鞍"理想，但它缺的是 Harness 文章里最实用的那几层。**

---

## 一、Ai_develop_os_exc 的先天优势

这个项目从 V1.0 架构文档开始就带着"先天约束"的基因：

### 1. 文件即协议，协议即物理

heartbeat.py 写心跳文件、lock_manager.py 管锁文件、override.py 管覆盖令。这些不是"建议模型遵守的规则"，是物理存在的文件，模型不写就超时被 kill。这已经是"约束即骨骼"了。

### 2. watchdog.ps1 是真正的"系统层"

它在 Claude 进程外面运行，检查心跳超时就杀进程。这不是 hook（hook 还在 Claude 进程内），这是操作系统级的约束。Harness 文章的五层里没有任何一层做到了这个程度。

### 3. handoff_executor.py 是交接仪式的代码实现

不是靠模型"记得"要交接，是物理文件驱动的交接流程。比 StateKanban 的"断点续作"强，也比 Harness 文章的 /handoff slash 命令更硬。

---

## 二、缺 Harness 文章里最值钱的三个东西

### 1. 记忆层 — 完全空白

Ai_develop_os_exc 的 node_protocol 里有"碎步时志"（每步写日志），但 _isa/ 目录下没有任何记忆管理模块。heartbeat_loop.py 只写心跳，不写决策日志。handoff_executor.py 交接时只传 lock 状态和任务描述，不传"为什么做这个决策"。

对比 Harness 文章的四工具分工（grep/向量/图谱/git log），Ai_develop_os_exc 连 grep 级别的"查历史"都没有。

**汲取方案**：在 _isa/ 下加 `memory.py`，每次 handoff 时自动生成 briefing.json（读最近 heartbeat + 读 _logs/ + 读 lock 状态），新 session 启动时读 briefing 而不是只读 lock。不需要上 RAG，先做轻量方案。

### 2. 验证证据 — 完全空白

process_manager.py 管进程、watchdog.ps1 管超时，但没有任何"你改了代码，证明你跑过测试"的机制。Harness 文章的"证据文件"设计（tsc 跑过才写时间戳 JSON）在这里可以直接用。

**汲取方案**：在 _shared/.claude/settings.json 的 PostToolUse hook 里加证据检查——改了 .py 文件后，hook 自动跑 pytest，通过才写 evidence/角色_时间戳.json。handoff_executor.py 交接时检查有没有未验证的改动。

### 3. 边界层 — 有但不够

settings.json 里有 pipe_guard hook，但 v2_isa 的 hook 配置比 StateKanban 简单很多——只有基本的路径拦截，没有 manifest 白名单机制。v2_agent 更弱，只有 PreToolUse 的基本拦截。

**汲取方案**：从 StateKanban 移植 pipe_manifest 机制——每个角色声明 inputs/outputs，hook 按白名单拦截。但要比 StateKanban 做得更好：让 heartbeat_loop.py 在启动时自检 manifest 声明与实际行为的一致性，把"外挂拦截"变成"内建自检"。

---

## 三、不需要汲取的

**认知层（7 种推理模式）** — Ai_develop_os_exc 的多角色架构天然解决了"卡住换思路"的问题。不需要在单个节点内做推理模式切换，因为卡住了是 override + 换节点实例的事。这是组织级的解决方案，比个体级的推理模式切换更可靠。

---

## 四、具体行动建议

| 优先级 | 做什么 | 从哪汲取 | 放在哪 |
|---|---|---|---|
| P0 | memory.py + briefing.json | Harness 记忆层 + StateKanban R7 设计 | _isa/memory.py |
| P1 | evidence_hook + evidence/ | Harness 证据文件机制 | _shared/.claude/settings.json |
| P2 | pipe_manifest 白名单 | StateKanban pipe_guard + manifest | _isa/manifest_check.py（内建自检，不是外挂 hook） |

---

## 五、关键原则：约束下沉，不加层

Ai_develop_os_exc 不应该照搬 StateKanban 的"外挂 hook"模式。它有 watchdog.ps1 这个操作系统级约束的基础，应该把约束下沉——manifest 检查放在 heartbeat_loop.py 的自检里，证据检查放在 handoff_executor.py 的交接流程里。

**让约束成为心跳和交接的一部分，而不是额外的 hook 层。**

这就是"先天长鞍"在 Ai_develop_os_exc 里的具体实现路径：不是加 hook，是让已有的物理机制（心跳、交接、看门狗）自带约束。
