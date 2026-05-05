---
name: civibbs-anti-patterns
description: CiviBBS 插件开发七大反模式和四大重构模式，写代码前必读
type: feedback
originSessionId: 43c16b9c-1ff9-402f-baba-0f4ceff9d7d1
---
# CiviBBS 插件开发规范

## 七大反模式（绝对不能违反）

1. **禁止 TOCTOU** — 不准先 exists() 再操作，必须直接操作+捕获异常
2. **所有 bool 参数必须类型校验** — isinstance(x, bool)
3. **必须处理目录/文件混淆** — 捕获 IsADirectoryError，Windows 用 errno 判断
4. **必须处理符号链接语义** — 原子操作天然处理
5. **日志用惰性格式化** — logger.debug("...%s", arg) 而非 f-string
6. **路径必须校验空字节** — "\x00" in path 检测
7. **抽取 _fail() 工具函数** — 消除重复的错误构造代码

## 四大重构模式

1. **统一错误出口** — _fail() / _ok() 两个函数
2. **强类型输入守卫** — _parse_inputs() 返回不可变对象或 error dict
3. **原子操作代替 TOCTOU** — 直接操作 + 异常分流
4. **跨平台目录检测** — _is_directory_error() 处理 Windows 差异

## definition.yaml 规范
- logic 用 **behavior** 而非 steps — 定义输入→输出映射，不写实现步骤
- error_codes 必须覆盖所有边界场景
- 每个错误码必须有 recovery 建议

## 模范代码
- `C:\civibbs\pipeline\done\delete_file\` — v1.1.0，已修复所有反模式

**Why:** Opus 评审发现所有插件都存在这些反模式，违反会导致竞态、类型错误、跨平台崩溃
**How to apply:** 每次写 CiviBBS 插件代码前必须对照此清单，以 delete_file v1.1.0 为模板
