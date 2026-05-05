# Netdef v1.0.2 — 项目归档

> 归档时间: 2026-04-21 | 作者: Yao Zhen | GitHub: yaozhen99/Netdef_Network-Definer
> 安全审计版本: v1.0.2 | 开发周期: 2026年初

## 项目定位

Windows 防火墙管理工具集，通过 bat/ps1 脚本管理 Windows Firewall 规则，包含 GUI 管理界面和 Wail2Ban 自动封禁系统。

## 核心组件

- **Netdef.bat** — 主菜单启动器，UAC 提权，9个功能选项
- **FirewallScripts/** — 防火墙配置脚本集
  - lan-config.bat — 信任网络入站规则（已改为环境变量+内联PS命令）
  - outdoor-config.bat/ps1 — 出站规则配置（含IP/端口验证）
  - cleanup-rules.bat/ps1 — 规则清理（限定 Netdef_*/Wail2Ban_* 前缀）
  - netdef-gui-launcher.ps1 — GUI启动器（IE11注册表恢复）
  - netdef-gui.ps1 — GUI管理界面
- **FirewallScripts/wail2ban/** — 自动封禁系统
  - wail2ban.ps1 — 主程序（HMAC状态完整性、日志轮转、命名管道优雅关停）
  - wail2ban-manager.bat — 管理脚本

## v1.0.2 安全加固

14项安全修复已实施：
- **Critical**: 动态PS1生成→环境变量+内联命令、ExecutionPolicy Bypass→RemoteSigned、UAC路径%0→%~dpnx0
- **Medium**: HMAC-SHA256状态文件完整性、命名管道优雅关停、日志轮转(10MB/3份)、IP格式验证、规则名前缀限定
- **Low**: IE11注册表恢复、错误处理改进

## 分支状态

- **main** — v1.0.2 稳定版，已推送 GitHub
- **feature/asr-hardening** — Atlas 的 ASR 安全加固改动（保留待讨论）

## 相关文档

- C:\Netdef_v1.0\README.md / README_CN.md
- C:\Netdef_v1.0\CHANGELOG.md / CHANGELOG_CN.md
- C:\Netdef_v1.0\SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
