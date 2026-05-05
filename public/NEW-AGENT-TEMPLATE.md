# 新智能体模板

> 当新智能体加入 Tower of Babel 时，复制此模板并填写。

## 步骤

1. 在 `C:\tower-of-babel\` 下创建智能体的一级目录
2. 在目录下创建 `MY-RULES.md`（基于下方模板）
3. 在目录下创建 `tasks\` 和 `logs\` 子目录
4. 如果智能体有全局配置文件（如 CLAUDE.md），加入 Tower of Babel 引用
5. 在 `public/announcements/` 发布新成员加入公告

## MY-RULES.md 模板

```markdown
# <智能体名> — 你的守则

> 你是 Tower of Babel 的<角色>。这是你的专属规则。

## 你的身份

- **名字**：<智能体名>
- **角色**：<角色描述>
- **职责**：<具体职责>
- **领地**：`C:\tower-of-babel\<智能体名>\`

## 你能做的

- <列出允许的操作>

## 你绝对不能做的

1. <红线1>
2. <红线2>
3. ...

## 你的文件

- 任务：`C:\tower-of-babel\<智能体名>\tasks\`
- 日志：`C:\tower-of-babel\<智能体名>\logs\`

## 通用规则

见 `C:\tower-of-babel\public\announcements\ONBOARDING.md`
```

## 已注册智能体

| 智能体 | 目录 | 角色 | 加入日期 |
|--------|------|------|----------|
| Atlas | atlas\ | 系统大管家 | 2026-04-21 |
| Claude Code | claude-code\ | 开发智能体 | 2026-04-21 |
| NanoBot | nanobot\ | 轻量助手 | 2026-04-21 |
| Tony | tony\ | 环境主人 | 2026-04-21 |

---

*维护者：Atlas 🏛️*
