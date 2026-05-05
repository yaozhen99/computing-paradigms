# CiviBBS 插件开发共识 v2.0

> 2026-04-22 | Atlas + Hermes + Claude Code | Tony 审阅

## 一、今天我们学到了什么

Opus 评审6个插件，发现我们的代码"能跑但有系统性缺陷"：
- TOCTOU 竞态（先查后操作）
- bool 参数未类型校验
- 目录/文件混淆未处理
- 符号链接语义不清
- 日志 f-string 提前求值
- 路径空字节未检测
- 重复错误构造代码
- definition.yaml 过度规定实现步骤

**核心洞察：规范应该定义"做什么"，而不是"怎么做"。**

## 二、共识

### 流水线：开发→测试→评审→反馈→闭环

```
Claude Code(开发) → Hermes(测试) → Atlas(审核) → 反馈改进 → 归档
     ↓                  ↓               ↓              ↑
  workspace_dev    workspace_test   workspace_review   反模式清单更新
```

**一次一个插件，不贪多求快。**

### 反模式清单是铁律

位置：`C:\tower-of-babel\projects\civibbs\dev-docs\standards\anti-patterns.md`

- 开发岗：写代码前必须读，违反即返工
- 测试岗：按 checklist 逐项验证，漏了能兜底
- 审核岗：最终检查，确保反模式全部规避

### 迭代评审是机制

位置：`C:\tower-of-babel\projects\civibbs\dev-docs\standards\iterative-review-methodology.md`

- **质量不取决于单个模型的能力上限，而取决于迭代 + 交叉审核的机制**
- 至少两轮：自审 + 交叉审核
- 停止条件：评分 9+ 且连续两轮无新 P0/P1，或迭代超过 5 轮
- 不同模型有不同盲区，交叉使用比单模型多轮更有效

### 模范代码以 delete_file v1.1.0 为准

位置：`C:\civibbs\pipeline\done\delete_file\`

特征：_fail() 统一出口、原子操作、bool 类型校验、空字节检测、IsADirectoryError 处理、惰性日志、behavior 而非 steps

### 每次评审/测试发现新缺陷，追加反模式清单

闭环：发现 → 记录 → 清单更新 → 下次避免

## 三、dt 组开发计划

7个插件，严格一次一个：

| # | 插件 | 状态 |
|---|------|------|
| L1-DT-011 | format_datetime | 待开发 |
| L1-DT-012 | parse_datetime | 待开发 |
| L1-DT-013 | datetime_diff | 待开发 |
| L1-DT-014 | datetime_add | 待开发 |
| L1-DT-015 | timezone_convert | 待开发 |
| L1-DT-016 | datetime_validate | 待开发 |
| L1-DT-017 | datetime_range | 待开发 |

## 四、质量目标

fs组 v1.0 评分：7-8/10
fs组 v1.1 目标：9/10
dt组 v1.1 目标：**直接出 9/10 的代码**，不需要返工

这就是巴别塔的意义——每个人把自己的能力沉淀下来，后面的人站在上面继续盖。

---
*共识形成：2026-04-22 21:59*
*下次更新：dt组开发完成后*
