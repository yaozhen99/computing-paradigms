# Netdef v1.0.1 版本功能更新记录

**版本**: v1.0.1  
**发布日期**: 2026-04-19  
**基于版本**: v1.0.0  
**类型**: Bug 修复 + 质量改进  

---

## 更新概要

v1.0.1 是 GitHub 发布准备版本，修复了 v1.0.0 评估中发现的全部 9 项问题，涵盖核心功能稳定性、安全合规、代码健壮性和国际化一致性。

---

## 详细更新列表

### 🔴 P0 阻断性修复

#### 1. Wail2Ban state.json 文件锁竞争 [FIX-01]
- **问题**: Save-State 函数每 10 秒直接写入 state.json，多实例或并发访问时产生 "文件正由另一进程使用" 错误，日志中累计 100+ 条错误
- **修复**: 
  - 引入 `Global\NetdefWail2BanState` Mutex 互斥锁
  - 采用原子写入策略（先写 .tmp 临时文件，再 rename 替换）
  - 添加 3 次重试机制，每次间隔 500ms
  - 读取 state.json 时同样加锁保护
- **影响文件**: `FirewallScripts/wail2ban/wail2ban.ps1`

#### 2. Wail2Ban 多实例启动防护 [FIX-02]
- **问题**: wail2ban-manager.bat 的进程检测中 PowerShell `exit` 只退出 PS 子进程，不阻止后续 `start` 命令，导致每次启动都创建新实例
- **修复**:
  - 使用 `Get-CimInstance Win32_Process` + CommandLine 匹配检测
  - PowerShell 返回 exit code（0=未运行，1=已运行）
  - BAT 层通过 `%errorlevel%` 条件判断
  - 检测到已运行时 `exit /b 1` 阻止后续执行
- **影响文件**: `FirewallScripts/wail2ban-manager.bat`

#### 3. setting.ini 真实 IP 地址移除 [FIX-03]
- **问题**: TrustedRanges 包含真实内网 IP 段 10.147.29.100-10.147.29.160
- **修复**: 替换为标准示例值 192.168.1.100-192.168.1.200
- **影响文件**: `FirewallScripts/setting.ini`

#### 4. 运行时文件 git 跟踪清理 [FIX-04]
- **问题**: wail2ban.log 和 state.json 可能被 git 跟踪
- **修复**: 
  - .gitignore 新增 `state.json`、`*.json.tmp`、`backup_*/` 规则
  - 保留 `.gitkeep` 维持目录结构
- **影响文件**: `.gitignore`

#### 5. LICENSE 和 README 占位符替换 [FIX-05]
- **问题**: LICENSE 中 `[Your Name/Netdef Contributors]`，README 中 `YOURNAME`、`[contact method]` 等占位符
- **修复**: 
  - LICENSE: `Netdef Contributors`
  - README: `netdef-project`
  - CHANGELOG: `security@netdef-project`
  - 联系方式改为 GitHub Issues/Discussions
- **影响文件**: `LICENSE`, `README.md`, `CHANGELOG.md`

#### 6. Netdef.bat 语法错误修复 [FIX-06]
- **问题**: 第 137 行 `ERROR: Cannot access...` 缺少 `echo` 命令
- **修复**: 改为 `echo [ERROR] Cannot access...` + `exit /b 1`
- **影响文件**: `Netdef.bat`

---

### 🟡 P1 改进项

#### 7. HTML GUI 英文本地化 [FIX-07]
- **问题**: GUI 界面全部为中文，与项目英文定位不一致
- **修复**:
  - `lang="zh-CN"` → `lang="en"`
  - `currentLang = 'zh'` → `currentLang = 'en'`
  - 所有 HTML 静态文本和 JS 动态文本替换为英文
  - i18n 框架完整保留，支持未来多语言切换
- **影响文件**: `FirewallScripts/netdef-gui-redesigned.html`

#### 8. INI 解析按段隔离 [FIX-08]
- **问题**: `findstr /b` 和 `find /i` 不区分 INI 段，同名 key 在不同段会冲突
- **修复**: 使用 PowerShell section-aware 解析器，逐行扫描跟踪当前段，仅在目标段内匹配
- **影响文件**: `FirewallScripts/lan-config.bat`, `FirewallScripts/outdoor-config.bat`

#### 9. 临时文件残留防护 [FIX-09]
- **问题**: lan-config.bat 生成的临时 PS1 脚本在 Ctrl+C 中断时不会被清理
- **修复**: 脚本启动时自动清理上次残留的 `netdef_*.ps1` 临时文件
- **影响文件**: `FirewallScripts/lan-config.bat`

---

## 升级指南

### 从 v1.0.0 升级到 v1.0.1

1. 备份当前 `setting.ini`（如已自定义配置）
2. 替换所有文件
3. 恢复 `setting.ini` 中的自定义配置（注意 TrustedRanges 格式不变）
4. 如果 Wail2Ban 正在运行，先停止再重启以加载新版本

### 配置兼容性

- `setting.ini` 格式完全兼容，无需修改
- `configs/*.ini` 模板文件无变更
- `logs/` 目录结构无变更
- `state.json` 格式无变更（但写入机制更安全）

---

## 已知限制

1. INI 解析器每次读取启动一个 PowerShell 进程，有约 200-400ms 开销
2. HTML GUI 的 i18n 翻译映射表目前仅英文，中文翻译保留在代码中供参考
3. Mutex 名称 `Global\NetdefWail2BanState` 在终端服务环境中可能需要调整权限

---

*文档结束*
