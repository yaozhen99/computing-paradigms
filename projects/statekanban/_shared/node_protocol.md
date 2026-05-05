# Agent 子代理模式 — 共享协议

## 目录权限隔离

每个角色只允许写入自己的输出目录：
- PM → 01_requirements/
- 架构师 → 02_design/
- DBA → 02_design/
- UI/UX → 02_design/
- 后端 → 03_source/backend/
- 前端 → 03_source/frontend/
- DevOps → 03_source/infra/
- 测试编写 → 04_testing/
- 测试执行 → 04_testing/
- 安全审计 → 04_testing/
- 审核员 → 05_review/
- 文档 → docs/
- 集成 → 05_delivery/
- 发布 → 05_delivery/

读取不限制，但写入必须严格隔离。

## 签字协议

每个角色完成后必须在 _pipes/lock_<角色>.json 签字：
```json
{"status":"completed|rejected","signed_by":"<角色>","timestamp":"<ISO8601>","retry_count":0}
```

rejected 时必须附带 issues 字段列出问题。

## 防御性写入

写文件时使用 tmp + rename 模式，防止中途崩溃导致数据损坏：
1. 写入 <filename>.tmp
2. 自检内容完整性
3. os.replace(<filename>.tmp, <filename>)

## 禁令

- 禁止写入非输出目录
- 禁止修改其他角色的 lock 文件
- 禁止与全局 AI 对话（只通过文件通信）
- 禁止在 AI 之间传递代码（文件是唯一真相）
