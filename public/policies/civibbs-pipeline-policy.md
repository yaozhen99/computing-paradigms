# CiviBBS 插件开发流水线制度

> 三岗分离，流水线作业，Atlas 统一调度

## 三岗定义

| 岗位 | 目录 | 职责 | 禁止 |
|------|------|------|------|
| **开发岗** | `C:\AI_exchange\workspace_dev\` | 按 definition.yaml 实现 execute.py + 触发机 | 不自测、不自审 |
| **测试岗** | `C:\AI_exchange\workspace_test\` | 按触发机独立验证，只看定义不看代码 | 不看实现代码、不改代码 |
| **审核岗** | `C:\AI_exchange\workspace_review\` | 审代码质量、规范一致性、出审核意见 | 不改代码，只出意见 |

## 流水线流程

```
Atlas 派发任务
    ↓
[开发岗] 拿任务文件 → 实现 execute.py + 触发机 → 产出到 workspace_dev/output/
    ↓ Atlas 搬运
[测试岗] 拿 definition.yaml + 触发机 → 验证 → 产出测试报告到 workspace_test/output/
    ↓ Atlas 判断
    ├─ 测试不通过 → 退回开发岗（附测试报告）
    └─ 测试通过 ↓
[审核岗] 拿代码 + 测试报告 → 审核代码质量 → 产出审核意见到 workspace_review/output/
    ↓ Atlas 判断
    ├─ 审核不通过 → 退回开发岗（附审核意见）
    └─ 审核通过 ↓
Atlas 归档 → 代码合入项目 → 任务状态更新
    ↓
Tony 终审（必要时）
```

## 目录结构

```
C:\AI_exchange\
├── workspace_dev\          # 开发岗工作区
│   ├── input\              # Atlas 放入任务文件 + definition.yaml
│   ├── output\             # 开发岗产出 execute.py + 触发机
│   └── return\             # 退回返工的任务（附测试报告/审核意见）
├── workspace_test\         # 测试岗工作区
│   ├── input\              # Atlas 放入 definition.yaml + 触发机 + execute.py
│   └── output\             # 测试岗产出测试报告
├── workspace_review\       # 审核岗工作区
│   ├── input\              # Atlas 放入代码 + 测试报告
│   └── output\             # 审核岗产出审核意见
├── Civibbs-githubv1.0\     # v1.0 框架（代码灵感）
├── V2.0_play\              # v2.0 代码（参考）
└── pipeline_done\          # 流水线完成的插件归档
```

## Atlas 调度规则

1. **一次只派一个任务**给开发岗
2. 开发完成后，Atlas 搬运产出物到测试岗 input
3. 测试通过后，Atlas 搬运到审核岗 input
4. 不通过则退回开发岗 return，附上原因
5. 审核通过后，Atlas 归档到 pipeline_done，更新任务状态
6. 同一时间只有一个插件在流水线上（串行，不并行）

## 三个 Claude Code 实例

| 实例 | 工作目录 | 用途 |
|------|---------|------|
| Claude-Dev | `C:\AI_exchange\workspace_dev\` | 只做开发 |
| Claude-Test | `C:\AI_exchange\workspace_test\` | 只做测试 |
| Claude-Review | `C:\AI_exchange\workspace_review\` | 只做审核 |

每个实例独立会话，互不污染。

## 任务状态流转

```
待开发 → 开发中 → 待测试 → 测试中 → 测试失败(→返工) → 待审核 → 审核中 → 审核失败(→返工) → 已完成
```

## 退回规则

- 测试不通过：必须附测试报告，说明哪个触发机失败、失败现象
- 审核不通过：必须附审核意见，说明违反哪条规范
- 退回最多 3 次，第 4 次 Atlas 介入分析根因
- 连续退回 3 次以上，升级给 Tony 决策

---
*版本：v1.0 | 2026-04-21 | Atlas 🏛️*
