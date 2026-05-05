# Netdef v1.0.1 修复计划书

**文档编号**: plan_github_release_fix_20260419  
**创建日期**: 2026-04-19  
**版本**: 1.0  
**状态**: 执行中  

---

## 一、项目背景

Netdef v1.0.0 已完成核心功能开发和基础测试，但在进行 GitHub 发布前评估时，发现了若干阻断性问题和改进项。本文档是 v1.0.1 版本的修复计划，目标是解决所有阻碍 GitHub 发布的问题，并提升项目整体专业度。

---

## 二、需求分析

### 2.1 核心需求

| 编号 | 需求描述 | 优先级 | 来源 |
|------|----------|--------|------|
| R-01 | Wail2Ban 核心功能稳定运行，无文件锁竞争 | P0-阻断 | 日志中 100+ 条错误记录 |
| R-02 | Wail2Ban 不允许多实例同时运行 | P0-阻断 | 多实例导致文件锁和资源浪费 |
| R-03 | 仓库中不包含真实 IP 地址等敏感信息 | P0-阻断 | 安全合规要求 |
| R-04 | 仓库中不包含运行时生成的日志和状态文件 | P0-阻断 | Git 仓库清洁度 |
| R-05 | LICENSE 和 README 中无占位符 | P0-阻断 | 开源合规要求 |
| R-06 | Netdef.bat 无语法错误 | P0-阻断 | 代码正确性 |
| R-07 | HTML GUI 语言与项目整体语言一致 | P1-重要 | 国际化用户体验 |
| R-08 | INI 配置解析按段隔离，避免 key 冲突 | P1-重要 | 代码健壮性 |
| R-09 | 临时脚本文件在异常退出时也能被清理 | P1-重要 | 系统清洁度 |

### 2.2 约束条件

- 所有修复不得改变现有用户配置文件的兼容性
- 修复后的功能行为应与原有设计意图一致
- 修复过程需保持项目目录结构不变

---

## 三、功能分析

### 3.1 修复项 1: state.json 文件锁竞争

**问题根因**:  
`wail2ban.ps1` 的 `Save-State` 函数每 10 秒写入 `state.json`，使用 `Out-File` 直接写入。当多个 Wail2Ban 实例同时运行，或外部进程读取该文件时，会产生文件锁竞争，导致大量错误日志。

**影响范围**: `wail2ban.ps1` 中的 `Save-State` 函数

**修复方案**:  
1. 为 `Save-State` 添加重试机制（最多 3 次，间隔 500ms）
2. 使用临时文件 + 原子替换策略（先写入临时文件，再 rename）
3. 添加文件写入互斥锁（Mutex）

**预期效果**: 消除文件锁竞争错误，确保状态持久化的可靠性

---

### 3.2 修复项 2: Wail2Ban 多实例启动

**问题根因**:  
`wail2ban-manager.bat` 的已运行检测逻辑中，PowerShell 的 `exit` 只退出 PS 子进程，不阻止后续的 `start` 命令执行。导致每次启动都会创建新的 Wail2Ban 实例。

**影响范围**: `wail2ban-manager.bat`

**修复方案**:  
1. 将检测逻辑移入 BAT 层，使用 `tasklist` 或 PowerShell 返回值判断
2. 检测到已运行时，在 BAT 层直接 `exit /b`，不再启动新实例
3. 添加 PID 文件机制作为辅助防重复启动手段

**预期效果**: 同一时刻只有一个 Wail2Ban 实例运行

---

### 3.3 修复项 3: setting.ini 真实 IP 替换

**问题根因**:  
`setting.ini` 中 `TrustedRanges = 10.147.29.100-10.147.29.160` 是真实内网 IP 段。

**影响范围**: `FirewallScripts/setting.ini`

**修复方案**:  
替换为通用示例值 `192.168.1.100-192.168.1.200`，与 README 和配置模板保持一致。

**预期效果**: 仓库中不含任何真实网络信息

---

### 3.4 修复项 4: 清理 git 跟踪的 log/state 文件

**问题根因**:  
`logs/wail2ban.log` 和 `logs/state.json` 是运行时生成的文件，不应被 git 跟踪。虽然 `.gitignore` 已有 `*.log` 规则，但文件可能已被早期 commit 跟踪。

**影响范围**: `FirewallScripts/logs/` 目录

**修复方案**:  
1. 从 git 索引中移除这些文件（`git rm --cached`）
2. 确保 `.gitignore` 规则正确覆盖
3. 保留 `.gitkeep` 以维持目录结构
4. 将 `state.json` 加入 `.gitignore` 显式规则

**预期效果**: git 仓库中不含运行时生成的文件

---

### 3.5 修复项 5: LICENSE 和 README 占位符替换

**问题根因**:  
- LICENSE: `Copyright (c) 2026 [Your Name/Netdef Contributors]`
- README: `YOURNAME`、`[contact method]`、`[security contact email]` 等占位符

**影响范围**: `LICENSE`、`README.md`

**修复方案**:  
替换所有占位符为合理的通用值（不使用个人真实信息，使用项目通用联系方式）。

**预期效果**: 文档中无未填充的占位符

---

### 3.6 修复项 6: Netdef.bat 语法错误

**问题根因**:  
第 137 行 `ERROR: Cannot access...` 不是有效的 batch 命令，缺少 `echo`。

**影响范围**: `Netdef.bat` 第 137 行

**修复方案**:  
将 `ERROR: ...` 改为 `echo [ERROR] ...`，并添加 `pause` 和 `exit /b 1`。

**预期效果**: 目录访问失败时正确显示错误信息

---

### 3.7 修复项 7: HTML GUI 中英文一致化

**问题根因**:  
`netdef-gui-redesigned.html` 的 UI 文本全部为中文，但项目整体为英文。`lang="zh-CN"` 也需要修改。

**影响范围**: `netdef-gui-redesigned.html`

**修复方案**:  
1. 将所有 UI 中文文本替换为英文
2. 修改 `lang` 属性为 `en`
3. 保留中英翻译映射表作为未来多语言支持的基础

**预期效果**: GUI 界面语言与项目整体语言一致

---

### 3.8 修复项 8: INI 解析按段隔离

**问题根因**:  
`lan-config.bat` 和 `outdoor-config.bat` 使用 `findstr /b "key"` 解析 INI 文件，但 INI 中不同段可能有相同的 key 名（如 `Enable` 在 `[Outbound]` 段，`Path` 在 `[Wail2Ban]` 段）。`findstr` 不区分段，可能匹配到错误的行。

**影响范围**: `lan-config.bat`、`outdoor-config.bat`

**修复方案**:  
1. 使用 PowerShell 辅助函数按段解析 INI
2. 或在 BAT 中使用更精确的 findstr 模式，限定段范围
3. 优先方案：将 INI 读取逻辑统一到 PowerShell 函数中，BAT 调用 PS 获取值

**预期效果**: 配置解析准确，不同段的同名 key 不会冲突

---

### 3.9 修复项 9: 临时文件残留风险

**问题根因**:  
`lan-config.bat` 生成临时 PS1 脚本后执行，如果用户 Ctrl+C 中断，临时文件不会被清理。

**影响范围**: `lan-config.bat`

**修复方案**:  
1. 使用 BAT 的 `trap` 机制（`goto :EOF` + 清理标签）处理中断
2. 在脚本开头检查并清理上次残留的临时文件
3. 使用固定前缀的临时文件名，便于识别和清理

**预期效果**: 无论正常退出还是异常中断，临时文件都能被清理

---

## 四、修复执行计划

### 4.1 阶段划分

| 阶段 | 内容 | 预计耗时 |
|------|------|----------|
| Phase 0 | 文件备份 | 5 min |
| Phase 1 | 修复项 1-6（P0 阻断性问题） | 60 min |
| Phase 2 | 修复项 7-9（P1 改进项） | 45 min |
| Phase 3 | 文档更新（README、CHANGELOG 等） | 20 min |
| Phase 4 | 项目总结和归档 | 15 min |

### 4.2 执行顺序

```
Phase 0: 备份
  └── 创建 backup/ 目录，复制所有待修改文件

Phase 1: P0 阻断性修复
  ├── 1.1 修复 state.json 文件锁竞争 (wail2ban.ps1)
  ├── 1.2 修复 Wail2Ban 多实例启动 (wail2ban-manager.bat)
  ├── 1.3 替换 setting.ini 真实 IP
  ├── 1.4 清理 git 跟踪的 log/state 文件
  ├── 1.5 替换 LICENSE 和 README 占位符
  └── 1.6 修复 Netdef.bat 语法错误

Phase 2: P1 改进项
  ├── 2.1 HTML GUI 英文化
  ├── 2.2 INI 解析按段隔离
  └── 2.3 临时文件残留防护

Phase 3: 文档更新
  ├── 3.1 更新 README.md
  ├── 3.2 更新 CHANGELOG.md
  └── 3.3 更新 GITHUB_SUBMISSION_CHECKLIST.md

Phase 4: 总结归档
  ├── 4.1 编写项目完成总结
  ├── 4.2 编写版本功能更新记录
  └── 4.3 归档所有过程文档
```

### 4.3 测试策略

每个修复项完成后，执行以下验证：

| 修复项 | 测试方法 | 验证标准 |
|--------|----------|----------|
| 文件锁竞争 | 连续运行 Wail2Ban 30 分钟 | 无 "正由另一进程使用" 错误 |
| 多实例启动 | 连续执行 `wail2ban-manager.bat` 3 次 | 只有 1 个 wail2ban 进程 |
| 真实 IP | 检查 setting.ini 内容 | 不含 10.147.x.x 地址 |
| git 清理 | `git status` 检查 | log/state 文件不在跟踪列表 |
| 占位符 | 全文搜索 `YOURNAME`、`[Your` | 无匹配结果 |
| 语法错误 | 执行 Netdef.bat 异常路径 | 正确显示错误信息 |
| GUI 英文化 | 启动 GUI 检查界面 | 所有文本为英文 |
| INI 解析 | 添加同名 key 测试 | 正确读取对应段的值 |
| 临时文件 | Ctrl+C 中断后检查 %temp% | 无 netdef_ 开头的残留文件 |

---

## 五、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 文件锁修复引入新 Bug | 低 | 高 | 充分测试，保留备份 |
| GUI 英文化遗漏中文 | 中 | 低 | 逐行检查 HTML |
| INI 解析重构破坏兼容性 | 中 | 高 | 保持 setting.ini 格式不变 |
| 临时文件清理误删 | 低 | 中 | 使用固定前缀，仅清理 netdef_ 开头 |

---

## 六、交付物清单

1. 修复后的所有源代码文件
2. 更新后的 README.md、CHANGELOG.md、LICENSE
3. 过程文档（进度日志、测试记录）
4. 项目完成总结文档
5. 版本功能更新记录

---

*文档结束*
