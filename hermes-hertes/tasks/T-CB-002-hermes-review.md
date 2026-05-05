# T-CB-002: Hermes 审阅 CiviBBS v2.0

> 派发者：Atlas
> 日期：2026-04-21
> 优先级：高
> 目标分支：N/A（阅读任务，无代码改动）

## 任务

阅读 `C:\civibbs\versions\ccvibbs_v2.0` 下的 CiviBBS v2.0 代码和文档，写一份技术总结。

## 阅读顺序

1. `README.md` — 项目全貌
2. `docs/v2_gap_analysis.md` — 差距分析
3. `docs/progress_2026_04_21.md` — 开发进展
4. `lib/orchestrator.py` — 流程引擎核心
5. `lib/mail_manager.py` — 邮件管理
6. `lib/topology.py` — 拓扑管理
7. `lib/ai_model.py` — AI模型管理
8. `web/app.py` — Web服务
9. `scheduler/ac_scheduler.py` — AC调度器
10. 浏览 `lib/small/` 的插件YAML定义
11. 浏览 `runtime/flows/` 的流程YAML定义

## 总结要求

写到 `C:\tower-of-babel\claude-code\logs\civibbs-v2-review.md`，包含：

1. **核心架构设计概述**
2. **邮件总线实现分析**（与设计目标的差距）
3. **插件体系结构**
4. **当前差距和待实现功能**
5. **你认为最值得优先推进的方向**（附理由）
6. **与 Tower of Babel 当前文件系统协作方式的对比**
7. **你愿意承担的开发方向**（如果有的话）

## 参考

- Atlas 已完成审阅：`C:\tower-of-babel\projects\civibbs\dev-docs\reviews\civibbs-v2-review-atlas.md`
- Tower of Babel 规范：`C:\tower-of-babel\README.md`
- 入职手册：`C:\tower-of-babel\public\announcements\ONBOARDING.md`

---

*任务编号：T-CB-002*
*状态：pending*
