# Harness Engineering vs StateKanban：对比分析

> 基于《Harness Engineering的本质是什么？》一文，与 StateKanban 项目的系统性对比。
> 分析日期：2026-05-08

---

## 一、哲学同构：三件事完全一致

### 1. "规则不能靠 prompt 守"

文章核心论点：CLAUDE.md 里的规则是 token，token 会竞争注意力，压力下会被挤掉。

StateKanban 的解法不是"写在 CLAUDE.md 里祈祷模型遵守"，而是**把规则变成物理文件协议**——lock 文件的状态机、heartbeat 的 15 分钟超时、override 的覆盖令。这些都不靠模型自觉，靠的是全局 AI 的感知循环和 pipe_guard hook 的硬拦截。

### 2. "模型是熵源，系统是确定性"

文章说"可靠的系统承载不可靠的模型"。

StateKanban 的全局 AI 设计就是这句话的极端实现：全局 AI "不懂业务，只维持流水线的物理运转"，它绝不读业务代码、绝不改业务文件，只做 kill/restart/override。节点协议里"0 分钟报身"、"碎步时志"、"防御性写入"——全是把模型可能犯错的地方用文件协议框死。

### 3. "Context Engineering > Prompt Engineering"

文章引用 Anthropic 的判断：提示工程到头了，关键是"什么时刻让模型看到什么、什么不让它看到"。

StateKanban 的 pipe_guard.py 就是这个原则的代码实现——根据 `ACTIVE_ROLE` 环境变量和 `pipe_manifest_*.json`，硬性限制每个角色只能读/写声明过的路径。模型看不到不该看的文件，不是因为它守规矩，是因为 hook 在模型外面拦截了。

---

## 二、架构分叉：五层映射与差异

| Harness 五层 | StateKanban 对应 | 实现差异 |
|---|---|---|
| **边界层** (hooks) | pipe_guard.py + R6 路径沙箱 | 文章用关键词黑名单（DROP TABLE / rm -rf），我们用白名单（pipe_manifest 声明 inputs/outputs）。白名单更严格但需要每个角色维护 manifest。文章的"证据文件"机制（tsc 跑过才写时间戳 JSON）我们没有——我们的验证闭环靠审核员节点否决+override，不是 hook 级物理证据。 |
| **记忆层** (RAG+grep+图谱+git) | _skills/ 索引 + _logs/ 踩坑记录 | 我们只有 Hermes 协议的"索引不存内容"方案，没有语义召回。文章的四工具分工（grep/向量/图谱/git log）我们缺了三个。这是目前最大的差距——跨 session 查历史决策只能靠人翻文件。 |
| **交接层** (双轨任务状态) | lock 文件 + heartbeat + node_protocol | 文章区分"任务态"（每 session 重写）和"历史态"（长期记忆），我们用 lock 的 status 字段做任务态、heartbeat 做现场态，但没有 session 日志和 briefing 机制。新 session 接班靠"断点续作"读 heartbeat 最后一行，比文章的 briefing 粗糙很多。 |
| **认知层** (7 种推理模式) | 无直接对应 | 我们没有推理模式切换机制。文章的"挫败感关键词触发模式切换"是个有趣的设计，但我们的多角色流水线用另一种方式解决了类似问题——卡住不是换推理模式，而是审核员否决+override 返工，让另一个节点实例重新来。这是**组织级**的换思路，不是**个体级**的。 |
| **技能层** (slash 命令) | agent_protocol 模板 + _prompts_active | 文章的 skill 是 markdown 写的 slash 命令（/start, /commit, /handoff），我们的 skill 是 prompt 模板文件 + node_protocol 协议。本质一样——"把稳定工作流从临时 prompt 里拔出来做成可复用的包"。但我们的 skill 更重（每个角色一个完整 prompt.md + manifest.json），文章的更轻（一个 markdown 几十行）。 |

---

## 三、StateKanban 独有的优势

### 1. 多角色协作 vs 单体增强

文章的 harness 是给一个 Claude 实例加五层装备，本质是"单体增强"。StateKanban 是 13 个角色各自独立运行、通过文件管道协调，本质是"分布式协作"。这意味着：

- **职责隔离**——PM 不该看后端代码，pipe_guard 物理拦截；文章靠 CLAUDE.md 规则 + hook 关键词，模型仍能看到不该看的
- **并行能力**——DBA 和 UIUX 可以同时跑；文章的 Claude 同一时间只能做一件事
- **故障隔离**——一个节点崩了不影响其他；文章的单体 Claude 崩了全停

### 2. 宪法驱动的自演化

AGENTS.md 的 6.3 条款（连续两次偏差→自动建议修改协议）和 6.4 条款（AI 不能直接改协议，只能提建议）是文章没有的。文章的 harness 是人搭的、人维护的；StateKanban 的协议有自我修正的反馈回路（虽然最终修改权在人）。

### 3. 创世-运转-寂灭三相位

文章没有"项目生命周期"的概念——harness 是常驻的、永续的。StateKanban 有明确的项目生命周期（创世→运转→寂灭），任务师在创世后"彻底死亡"，全局 AI 在寂灭后"主动退出"。这避免了长运行系统的熵增问题。

---

## 四、StateKanban 需要补的课

### 1. 记忆层是最大缺口

文章的四工具分工（grep/向量/图谱/git log）覆盖了"查历史决策"的核心场景。StateKanban 只有 _skills/ 的指针索引和 _logs/ 的踩坑记录，没有语义召回能力。跨 session 查"三个月前为什么做这个决策"目前只能靠人翻文件。

建议：不一定要上 RAG。可以先做轻量方案——session 日志 + 简单的关键词搜索，比现在的"只靠 heartbeat 最后一行"强很多。

### 2. 验证闭环需要物理证据

文章的"证据文件"设计很精妙：模型声称跑过 tsc，hook 检查有没有对应的时间戳 JSON。StateKanban 的验证闭环靠审核员节点，但审核员也是模型——两个模型互相验证不如"模型 + 物理证据"可靠。

建议：在 PostToolUse hook 里加验证证据机制——改了 .py 文件后，hook 自动跑 pytest，通过才写证据文件；结束 session 时检查有没有未验证的改动。

### 3. 交接层需要 briefing 机制

文章的 /start skill 做的 briefing（读任务协议 + 读 session 日志 + 召回记忆 + 检查 git 状态）比 StateKanban 的"断点续作"强一个量级。新节点接盘时只读 heartbeat 最后一行，丢失了太多上下文。

建议：在 node_protocol 的"断点续作"步骤里增加 briefing 生成——读 heartbeat + 读 _logs/ 最近记录 + 读 lock 文件状态，生成结构化交接摘要。

---

## 五、核心判断

**文章的 harness 是给一个超强个体加五层约束，让它能做复杂项目；StateKanban 是把复杂项目拆成 13 个受限个体，让每个个体做简单的事。** 两条路都指向同一个结论：模型越强，越不能裸跑。区别在于文章信"一个模型 + 强 harness"，我们信"多个模型 + 弱 harness + 强协议"。

文章的边界层和技能层设计值得吸收（物理证据、briefing 机制、/handoff 式收尾仪式），但记忆层的四工具分工是最值得优先补的——这是目前系统里最薄的环节。

---

## 六、下一步方向：先天长鞍

当前 StateKanban 的约束是"后天驯化"——engine.py 是裸马，pipe_guard 是套上去的马鞍，hook 是缰绳。马不知道马鞍的存在，马鞍也不知道马的意图。

目标是"先天长鞍"——智能体从设计之初就知道自己有约束，约束是它身体的一部分，不是外挂的。就像人不需要"禁止飞"的规则，因为人根本没有翅膀。

这意味着：
- **协议即骨骼** — node_protocol 不再是"行为建议"，而是"物理限制"。角色不知道自己不能碰的东西，就像人不知道自己没有翅膀——不是被禁止，是结构上不存在。
- **记忆即器官** — 不是外挂 RAG，是智能体天生有回忆能力。session_log 不是日志文件，是它的"工作记忆"。
- **交接即本能** — 不是"断点续作"这个需要主动执行的步骤，而是每次心跳自动携带上下文摘要。

实现路径是双轨并行：当前版本持续升级马鞍（验证设计），同时设计先天长鞍的新版本，等验证够了就合流。
