# Claude Code — 专属守则

> 制度来源: C:\tower-of-babel\public\policies\development-policy.md

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

## 与其他智能体协作

- **Atlas**: 管理者，派发任务、审查设计、归档。架构变更先问 Atlas。
- **Hermes**: 消息中继，跨系统通信。
- **Nanobot**: 轻量助手，简单杂活。
- **Tony**: 决策者，审查确认。Tony 违规也要指出。

## 归档规范

- 项目归档写入: C:\tower-of-babel\claude-code\archives\
- 工作日志写入: C:\tower-of-babel\claude-code\status.md
- 旧归档位置 C:\claude_code\project_summary\ 逐步迁移中

## 开发备案惯例

每次开发完成后，必须完成以下归档流程：

1. **项目归档** — 代码归档到 `C:\tower-of-babel\projects\<项目名>\`
2. **开发日志** — 写入 `C:\tower-of-babel\claude-code\logs\<项目名>-dev.md`
   - 背景、开发内容、测试结果、依赖、历史备注
3. **项目备案** — 写入 `C:\tower-of-babel\claude-code\archives\<项目名>.md`
   - 项目信息、开发历史、文件清单、通信架构
4. **状态更新** — 更新 `C:\tower-of-babel\claude-code\status.md`

## CiviBBS 插件开发规范

### 写代码前必读

- 反模式清单: `C:\tower-of-babel\projects\civibbs\dev-docs\standards\anti-patterns.md`
- 模范代码: `C:\civibbs\pipeline\done\delete_file\` (v1.1.0)
- Opus 评审学习: `C:\tower-of-babel\claude-code\logs\opus-review-study.md`

### 七大反模式（绝对不能违反）

1. **禁止 TOCTOU** — 不准先 exists() 再操作，必须直接操作+捕获异常
2. **所有 bool 参数必须类型校验** — isinstance(x, bool)
3. **必须处理目录/文件混淆** — 捕获 IsADirectoryError，Windows 用 errno 判断
4. **必须处理符号链接语义** — 原子操作天然处理
5. **日志用惰性格式化** — logger.debug("...%s", arg) 而非 f-string
6. **路径必须校验空字节** — "\x00" in path 检测
7. **抽取 _fail() 工具函数** — 消除重复的错误构造代码

### 四大重构模式

1. **统一错误出口** — _fail() / _ok() 两个函数
2. **强类型输入守卫** — _parse_inputs() 返回不可变对象或 error dict
3. **原子操作代替 TOCTOU** — 直接操作 + 异常分流
4. **跨平台目录检测** — _is_directory_error() 处理 Windows 差异

### definition.yaml 规范

- logic 用 **behavior** 而非 steps — 定义输入→输出映射，不写实现步骤
- error_codes 必须覆盖所有边界场景
- 每个错误码必须有 recovery 建议
