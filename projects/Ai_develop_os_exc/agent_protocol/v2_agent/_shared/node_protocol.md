# Agent 子代理模式 — 共享协议

## 物理隔离（PreToolUse Hook 管道）

每个角色的文件读写由 **pipe_guard.py**（PreToolUse hook）在基础设施层面强制执行，不依赖 prompt 禁令。

### 管道清单（Pipe Manifest）

全局 AI 拉起子代理前，生成 `_pipes/pipe_manifest_<角色>.json`：

```json
{
  "role": "backend",
  "inputs": ["02_design/", "_system/approved_tech_stack.json"],
  "outputs": ["03_source/backend/", "_pipes/lock_backend.json"],
  "created_at": "<ISO8601>",
  "agent_id": "<子代理ID>"
}
```

### 管道规则

- **读操作**（Read/Glob/Grep）：`file_path` 必须在 `inputs` 或共享只读路径（`_system/`, `_skills/`）内
- **写操作**（Write/Edit）：`file_path` 必须在 `outputs` 内
- **Bash 命令**：启发式检查 `>`/`>>`/`tee` 重定向目标是否在 `outputs` 内（已知限制：`cat`/`head` 等读命令无法拦截）
- **越权操作**：pipe_guard.py 返回 `permissionDecision: "deny"`，工具调用被阻断
- **全局 AI**：`ACTIVE_ROLE` 未设置时管道放行，不受限制

### 角色管道映射

| 角色 | inputs | outputs |
|:---|:---|:---|
| PM | _system/ | 01_requirements/ |
| 架构师 | 01_requirements/, _system/ | 02_design/ |
| DBA | 01_requirements/, 02_design/ | 02_design/ |
| UI/UX | 01_requirements/, 02_design/ | 02_design/ |
| 后端 | 02_design/, _system/ | 03_source/backend/ |
| 前端 | 02_design/, _system/ | 03_source/frontend/ |
| DevOps | 02_design/, _system/ | 03_source/infra/ |
| 测试编写 | 02_design/, 03_source/ | 04_testing/ |
| 测试执行 | 04_testing/, 03_source/ | 04_testing/ |
| 安全审计 | 03_source/, 04_testing/ | 04_testing/ |
| 审核员 | 01_requirements/, 02_design/, 03_source/, 04_testing/ | 05_review/ |
| 文档 | 01_requirements/, 02_design/, 03_source/ | docs/ |
| 集成 | 02_design/, 03_source/, 04_testing/, 05_review/ | 05_delivery/ |
| 发布 | 05_delivery/ | 05_delivery/ |

### 管道生命周期

1. 全局 AI 拉起子代理前：生成 pipe_manifest，设置 `ACTIVE_ROLE` 环境变量
2. 子代理运行中：每次工具调用经 pipe_guard.py 审查
3. 子代理完成后：删除 pipe_manifest，清除 `ACTIVE_ROLE`

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
