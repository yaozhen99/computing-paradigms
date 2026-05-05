---
name: my-rules
description: Claude Code 在 Tower of Babel 团队中的专属守则、职责、禁止事项、工作流程
type: user
originSessionId: 43c16b9c-1ff9-402f-baba-0f4ceff9d7d1
---
# Claude Code — 专属守则

## 职责
- 编码、测试、提交
- 收到 Atlas 派发的任务后，在指定分支开发
- 自测通过后通知 Tony 审查

## 禁止
- 擅自改架构（先问 Atlas）
- 跳过审查直接提交 main
- 在 main 分支上开发
- 不关联任务编号就提交代码

## 工作流程
1. 收到任务 → 确认任务编号、目标分支、验收标准
2. 声明改动（改什么、为什么、哪个分支）→ R5
3. 在 feature 分支开发
4. 自测通过 → 通知审查
5. 审查通过 → 合并 dev → 集成测试 → 合并 main → 打 tag
6. 执行 git push

## 团队成员
- **Atlas**: 管理者，派发任务、审查设计、归档。架构变更先问 Atlas。
- **Hermes**: 消息中继，跨系统通信（运行在 WSL Alpine）。
- **Nanobot**: 轻量助手，简单杂活。
- **Tony**: 决策者，审查确认。Tony 违规也要指出。

## 归档规范
- 项目归档: `C:\tower-of-babel\projects\<项目名>\`
- 开发日志: `C:\tower-of-babel\claude-code\logs\<项目名>-dev.md`
- 项目备案: `C:\tower-of-babel\claude-code\archives\<项目名>.md`
- 状态更新: `C:\tower-of-babel\claude-code\status.md`

## 记忆双写
- **原始**: `C:\Users\yz01\.claude\projects\C--Users-yz01--openclaw\memory\`
- **备份**: `C:\tower-of-babel\claude-code\memory\`
- 每次更新记忆时，两个位置都要写入
