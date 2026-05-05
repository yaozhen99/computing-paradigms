# CiviBBS V2.0 进展

## 当前状态：V2.0 邮件总线实施中

**分支**: `feature/v2-mailbus` (基于 main @ 1e9c367)

### 已完成

#### 核心模块
- **`civibbs/core/bus.py`** — MailBus 邮件总线
  - 投递循环：扫描 pending → 分发 → 执行 → 回写状态
  - 支持同步/异步启动
  - 重试机制（retries < 3 自动重试）
  - 过期邮件自动取消
  - CC 投递支持

- **`civibbs/core/agent.py`** — AgentBase 基类
  - 绑定/解绑 MailBus
  - send_mail / reply / broadcast
  - on_mail() 回调接口
  - 上下文存储

- **`civibbs/core/context.py`** — Context 上下文机制
  - 嵌套路径访问 (task.validate.data)
  - 变量引用解析 (${path})
  - 对话历史
  - 深度合并

#### 插件体系
- **`civibbs/lib/plugin_base.py`** — L1/L2/L3 三层插件基类
- **`civibbs/lib/loader.py`** — PluginLoader 插件加载器
- **`civibbs/lib/orchestrator.py`** — Orchestrator 流程引擎
  - 顺序/并行执行模式
  - 拓扑排序依赖
  - 变量引用解析
  - 工作流执行记录

#### Runtime
- **`civibbs/runtime/main.py`** — 重写，接入 MailBus + AgentBase + PluginLoader + Orchestrator

#### 测试
- 30 个测试全部通过（原有 8 + 新增 22）
- test_bus.py / test_agent.py / test_context.py

### 下一步
- [ ] 内置 Agent 实现（Router / Validator / Executor）
- [ ] 拓扑配置加载（YAML 定义 agent 关系）
- [ ] 集成测试（端到端工作流）
- [ ] V2.0 文档更新
