# Claude Code 开发守则

> 每次启动开发任务前必须阅读

## 红线（绝对不可违反）

1. **不在 main 分支上开发** — 所有开发在 feature/ 或 dev 分支
2. **不跳过审查直接合并到 main** — 合并前必须经 Tony 审查
3. **不擅自改架构** — 架构变更先跟 Atlas 讨论
4. **不在代码中硬编码密钥/Token** — 凭据只走环境变量
5. **每次改动关联任务编号** — 不做无编号的改动

## 开发流程

```
1. 收到任务（Tower of Babel 或 Tony 直接指派）
2. 确认任务编号、目标分支、设计文档
3. 从 dev 建 feature/<功能名> 分支
4. 在 feature 分支上开发
5. 自测通过 → 通知 Tony 审查
6. 审查通过 → 合并到 dev → 集成测试
7. 集成测试通过 → 合并到 main → 打 tag
8. git push
```

## 通信

- 任务目录：`C:\tower-of-babel\claude-code\tasks\`
- 工作日志：`C:\tower-of-babel\claude-code\logs\`
- 公共制度：`C:\tower-of-babel\public\policies\`

## 完整制度

见 `C:\tower-of-babel\public\policies\development-policy.md`

---

*版本：v2.0 | 2026-04-21 | Atlas 🏛️*
