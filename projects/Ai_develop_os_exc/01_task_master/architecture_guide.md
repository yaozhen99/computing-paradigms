# 任务师操作手册 — 架构规则

> 本文档从"纯文件驱动 AI 操作系统架构 V1.0"提炼，专供任务师执行时参考。
> 原始文档保留于项目根目录，作为人类参考和版本溯源。

## 宪法十条（任务师必须遵守的底线）

1. 文件是唯一的真相。AI之间零对话，零API互调，零共享内存。
2. 凭证不可篡改。所有管道文件必须携带时间戳、角色和签字。
3. 影子写入。永远先写.tmp，自检无误后执行物理拷贝覆盖。
4. 心跳即存档。节点每推进一步，必须覆盖更新心跳时志。
5. 0分钟报身。节点启动的第一件事，是在心跳文件中写明时间戳和角色名（不写 PID，进程管理由看门狗负责）。
6. 只存索引不存内容。技能文件只写指针，严禁投喂大段历史文本。
7. 遇到矛盾，推倒重来。绝对禁止修补过去的错误文件，只发覆盖令。
8. 遗忘即永生。全局AI每次循环必须清空记忆，只靠存盘点恢复上下文。
9. 熔断与上报。连续失败3次停止重启，标红等待人类介入。
10. 宪法不写刑法。架构师只画红线与定义接口，AI自主决定实现细节。

## 工作区目录结构（任务师必须创建）

```
workspace/
├── _system/
│   ├── user_input.md
│   ├── system_state.json
│   ├── proposed_tech_stack.json
│   ├── approved_tech_stack.json    # [人类亲手创建]
│   └── pipeline_blueprint.json
├── _scripts/
│   └── run_node_角色.sh
├── _pipes/
│   ├── lock_角色.json
│   └── override_时间戳.json
├── _heartbeats/
│   └── hb_角色.md
├── _skills/
│   └── idx_角色.json
├── _logs/
│   └── fix_xxx.md
├── _prompts_active/
│   └── active_prompt_角色.md
├── _shared/                        # 从 agent_protocol/_shared/ 复制
│   ├── node_protocol.md
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── doc_templates/              # 文档格式模板
│   └── skills/                     # 通用模式库
├── 01_requirements/
├── 02_design/
├── 03_source/
│   ├── backend/
│   ├── frontend/
│   └── infra/
├── 04_testing/
├── 05_delivery/
├── docs/                        # 工作文档
│   ├── plans/
│   ├── notes/
│   └── summaries/
```

## 三相位生命周期（任务师负责相位一）

### 相位一：创世（任务师执行，人类物理卡口）
1. 分析需求，输出技术选型提案
2. 上锁等待：system_state.json → {status: AWAITING_TECH_APPROVAL}
3. **人类圣裁**：人类亲手创建 approved_tech_stack.json
4. 铸造世界：建目录、写Prompt、生成启动脚本、写蓝图
5. 交接：system_state.json → {status: READY}，任务师消亡

### 相位二：运转（全局 AI 常驻守护）
- 任务师不参与，由全局 AI 接管

### 相位三：寂灭（发布经理 → 全局 AI）
- 任务师不参与

## 全局 AI 感知循环规则（任务师需理解，用于写蓝图）

| 监控目标 | 判定条件 | 裁决动作 |
|---|---|---|
| 节点生命 | 心跳超时15分钟 | 写 signal_kill 信号文件，看门狗执行 kill，retry+1，≥3则标红BLOCKED |
| 流程推进 | 前置lock全部completed | 拉起下一批节点 |
| 异常覆盖 | 发现override文件 | 暂停流转，执行返工 |
| 人类强控 | user_input含#OVERRIDE | 清空lock，强杀节点，重启流水线 |

## 节点底层协议（任务师写Prompt时必须包含引用）

所有岗位 Prompt 中引用 `_shared/node_protocol.md`，该文件包含7条底层协议。**注意：`@_shared/node_protocol.md` 是引用标记，不是自动展开指令，铸造时必须替换为显式指令："读取 _shared/node_protocol.md 并严格遵守其中所有规则。"**
1. 0分钟报身
2. 断点续作
3. 碎步时志
4. 防御性写入
5. 经验沉淀 (Hermes)
6. 终局交接
7. 编码纪律 (agent_protocol)

## 审核员特殊规则

审核员只判不改。否决时不修改代码，只生成 override_时间戳.json，由全局AI拉起返工。
