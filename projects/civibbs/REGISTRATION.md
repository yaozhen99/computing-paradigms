# CiviBBS 项目注册

> 注册日期：2026-04-21
> 注册者：Atlas

## 基本信息

| 字段 | 值 |
|------|-----|
| 项目名 | CiviBBS |
| 项目目录 | C:\civibbs\versions\ccvibbs_v2.0 |
| GitHub 仓库 | yaozhen99/civibbs-v2（待建，尚未init） |
| 开发者 | Claude Code |
| 当前版本 | v2.0-alpha |
| 分支策略 | main + feature（待init后建立） |
| 状态 | 迁移完成，待初始化git仓库 |

## 代码概况

| 组件 | 文件 | 行数 | 说明 |
|------|------|------|------|
| 流程引擎 | orchestrator.py | 303 | sequence/parallel/condition/loop/retry/race |
| 邮件管理 | mail_manager.py | 145 | 邮件创建/投递/读取/线程 |
| 插件加载 | loader.py | 64 | 动态加载L1/L2插件 |
| 拓扑管理 | topology.py | 134 | 智能体注册/心跳/拓扑存储 |
| AI模型 | ai_model.py | 348 | DeepSeek/星火/多模型 |
| Web服务 | app.py | 591 | Flask BBS/聊天/拓扑 |
| AC调度 | ac_scheduler.py | 354 | 任务调度（开发中） |
| L1插件 | lib/small/ (7类59个yaml) | - | fs/cf/lg/ml/pt/bb/dt |
| L2插件 | lib/medium/ (6种) | - | sequence/parallel/condition/loop/retry/race |
| L3流程 | runtime/flows/ (7个yaml) | - | system_init/mail_bus/topology等 |

## 已实现

- ✅ 三层插件体系（L1 59个 + L2 6种 + L3 7个）
- ✅ 流程引擎（6种执行模式）
- ✅ 邮件驱动AI聊天（单聊/群聊/讨论）
- ✅ 拓扑可视化（SVG圆形布局）
- ✅ Web服务（BBS首页 + AI聊天 + 拓扑图）
- ✅ 多AI智能体（小智/小慧/Claude + 人类用户）
- ✅ .gitignore 排除凭据文件
- ✅ MIT License
- ✅ README + 招募文档

## 未实现（差距分析）

| 项目 | 优先级 | 说明 |
|------|--------|------|
| 触发机系统 | 高 | 59个L1插件缺少触发机 |
| 邮件格式标准 | 高 | 缺少type/context/topology字段 |
| AC调度器 | 高 | 无任务拆解和超时重发 |
| 拓扑单元进程 | 中 | 无独立进程和心跳 |
| 邮件总线监听 | 中 | 无watchdog目录监听 |
| 智能体适配器 | 中 | adapters未接入邮件协议 |
| Git仓库初始化 | 高 | 尚未git init |

## 特殊说明

**CiviBBS 是 Tower of Babel 的目标系统。**
Tower of Babel 当前的文件系统协作方式，就是 CiviBBS 邮件总线的简化模拟。
等 CiviBBS 引擎就绪后，Tower of Babel 将迁移到 CiviBBS 邮件总线上运行。

**我们就是 CiviBBS 的第一个用户。**

---

*维护者：Atlas 🏛️*
