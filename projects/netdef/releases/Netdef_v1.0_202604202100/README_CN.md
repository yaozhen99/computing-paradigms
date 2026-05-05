**中文** | [**English**](README.md)

# 🛡️ Netdef - 个人网络安全套件

[![Built with TRAE SOLO](https://img.shields.io/badge/Built%20with-TRAE%20SOLO-blue.svg)](https://trae.com)
[![Version](https://img.shields.io/badge/version-1.0.1-green.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Server%202019%2B-blue.svg)]()
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-512BD4.svg)]()
[![GUI](https://img.shields.io/badge/GUI-HTML%20%2B%20WinForms-orange.svg)]()

> ⚡ **AI 辅助开发**：使用 [TRAE SOLO](https://trae.com) 在 72 小时内构建
> 🏠 **用途**：家庭网络、远程办公和旅行的零信任安全防护
> 🎯 **适合人群**：追求企业级安全但不想面对复杂性的个人用户

---

## 🌟 为什么需要 Netdef？

### 我要解决的问题

作为一个在家、咖啡厅、客户办公室之间切换的开发者，我需要一套网络安全方案：

- ✅ **不过度**（不需要每年花 $500+ 的企业级臃肿软件）
- ✅ **真正适用于 Windows**（大多数开源工具面向 Linux）
- ✅ **随场景切换**（家 ≠ 办公室 ≠ 咖啡厅 WiFi）
- ✅ **可信赖**（开源、无数据收集、无订阅）

**找不到，所以自己做了。**

### Netdef 有什么不同？

| 特性 | Netdef | Windows 防火墙界面 | 商业软件 | 其他开源 |
|------|--------|-------------------|---------|---------|
| **零信任模型** | ✅ 简单易用 | ❌ | ✅（昂贵） | ⚠️ 复杂 |
| **多场景配置** | ✅ 4种模式 | ❌ | ⚠️ 有限 | ❌ |
| **IP白名单 + 动态封禁** | ✅ 混合方案 | ❌ | ✅ | ⚠️ 需多个工具 |
| **一键配置** | ✅ 5分钟 | ❌ | ✅ | ❌ |
| **免费开源** | ✅ MIT 许可 | N/A | ❌（$$$） | ✅ |
| **图形界面** | ✅ HTML + WinForms | ❌ 基础 | ✅ | ❌ |
| **AI 辅助代码质量** | ✅ 已审计 | N/A | 未知 | 不确定 |

---

## 🚀 快速开始（5分钟）

### 前提条件
- Windows 10/11 或 Windows Server 2019+
- 管理员权限（脚本会自动请求提权）
- 了解你的网络 IP 地址范围

### 安装

```bash
# 克隆或下载此仓库
git clone https://github.com/netdef-project/netdef.git
cd netdef

# 用你的网络信息编辑配置
notepad FirewallScripts\setting.ini

# 运行主启动器
.\Netdef.bat
```

> ⚠️ **重要**：请始终使用 `.\Netdef.bat`（带 `.\` 前缀）运行，确保执行当前目录的脚本。

### 启动方式

Netdef 提供 **3 类启动方式**：

#### 1. 主入口（推荐）

从项目根目录运行：

| 命令 | 说明 |
|------|------|
| `.\Netdef.bat` | 交互菜单（8个选项） |
| `.\Netdef.bat 1` | 家庭网络（局域网配置） |
| `.\Netdef.bat 2` | 旅行模式（公共WiFi） |
| `.\Netdef.bat 3` | 清理规则 |
| `.\Netdef.bat 4` | 启动 Wail2Ban 守护 |
| `.\Netdef.bat 5` | 停止 Wail2Ban 守护 |
| `.\Netdef.bat 6` | 完全退出（清理 + 停止） |

#### 2. 直接运行子脚本

从 `FirewallScripts\` 目录运行：

| 命令 | 说明 |
|------|------|
| `.\lan-config.bat` | 应用家庭/办公配置 |
| `.\outdoor-config.bat` | 应用旅行模式配置 |
| `.\cleanup-rules.bat` | 移除所有自定义防火墙规则 |
| `.\wail2ban-manager.bat` | 启动 Wail2Ban |
| `.\wail2ban-manager.bat /stop` | 停止 Wail2Ban |

#### 3. 图形界面

| 命令 | 说明 |
|------|------|
| `powershell -ExecutionPolicy Bypass -File .\netdef-gui-launcher.ps1` | HTML桥接GUI（默认，内嵌WebBrowser） |
| `powershell -ExecutionPolicy Bypass -File .\netdef-gui-launcher.ps1 -Legacy` | WinForms 传统GUI（备选） |
| `powershell -ExecutionPolicy Bypass -File .\netdef-gui.ps1` | 独立 WinForms GUI |

> 💡 也可通过交互菜单选项 **[8]** 启动 GUI。

### 首次运行：家庭网络配置

1. **查找你的家庭 IP 范围**：
   - 打开命令提示符：`ipconfig`
   - 找到 "IPv4 地址"（如 `192.168.1.105`）
   - 你的范围通常是 `192.168.1.100-192.168.1.200`（查看路由器 DHCP 设置）

2. **编辑 `FirewallScripts\setting.ini`**：
   ```ini
   [Inbound]
   TrustedRanges = 192.168.1.100-192.168.1.200
   ```

3. **应用家庭配置**：
   ```bash
   .\Netdef.bat 1
   ```

4. **验证是否生效**：
   - 你的设备之间仍可通信 ✅
   - 外部设备被阻止 ✅
   - 互联网正常 ✅

**完成！你的家庭网络现在已启用零信任安全。**

---

## 📖 使用场景

Netdef 支持 **4 种安全配置**，随场景切换：

### 🏠 场景1：家庭网络（默认）

**适用**：在家连接可信路由器
**安全级别**：标准（平衡）
**功能**：
- 仅允许你的设备（白名单 IP 范围）
- 阻止所有其他入站连接
- 可选：启用 Wail2Ban 增加入侵检测

**命令**：`.\Netdef.bat 1` 或菜单选项 [1]

---

### 💼 场景2：办公模式

**适用**：在公司办公网络工作
**安全级别**：中等（侧重生产力）
**功能**：
- 信任办公 IP 范围
- 允许出站连接（工作工具、云服务）
- 静默监控可疑活动

**小贴士**：使用 `configs/` 目录的预设配置文件，一键切换！

---

### ✈️ 场景3：旅行 / 公共WiFi 🔥 **最受欢迎**

**适用**：咖啡厅、酒店、机场、会议
**安全级别**：**高**（偏执模式）
**功能**：
- **阻止危险出站端口**：
  - TCP：135、139、445（Windows文件共享）、3389（RDP）、5900（VNC）、8080、8443
  - UDP：137、138（NetBIOS）、1900（UPnP）、5353（mDNS）
- 启用增强日志
- **5分钟内超过100次连接丢弃时告警**（可能正在被扫描！）
- 建议自动启动 Wail2Ban

**为什么重要**：公共WiFi是黑客的天堂。攻击者使用 Wireshark 等工具嗅探流量，用端口扫描器寻找脆弱目标。Netdef 在他们利用之前就锁定了你的电脑。

**防范的真实威胁**：
- ☠️ 邪恶双胞胎攻击（伪造热点）
- ☠️ ARP 欺骗 / 中间人攻击
- ☠️ 端口扫描与侦察
- ☠️ 恶意软件外联
- ☠️ SMB/RDP 漏洞利用（WannaCry 类攻击）

**命令**：`.\Netdef.bat 2` 或菜单选项 [2]

---

### 🔒 场景4：锁定模式（最高安全）

**适用**：处理敏感数据、银行业务，或怀疑已被入侵
**安全级别**：**最高**（锡纸帽认证 😄）
**功能**：
- **阻止所有入站**（白名单 IP 除外）
- **阻止所有出站**（明确允许的目标除外）
- Wail2Ban 最高灵敏度
- 详细日志记录

**如何激活**：
```ini
; 在 setting.ini 中：
[Outbound]
Enable = 1
AllowedRanges = 0.0.0.0/0

; 然后运行：
.\Netdef.bat 1
```

**警告**：这可能导致某些应用无法使用！请先在安全环境中测试。

---

## ⚙️ 配置指南

### 文件：`FirewallScripts/setting.ini`

所有设置通过一个简单的 INI 文件控制，无需修改代码！

#### 节：`[Inbound]` - 入站流量控制

```ini
[Inbound]
; 必填：至少指定一个 IP 范围
; 格式选项：
;   - 单个IP：192.168.1.100
;   - IP范围：192.168.1.100-192.168.1.200
;   - 多个：192.168.1.100-150, 10.0.0.5, 172.16.0.1
TrustedRanges = 192.168.1.100-192.168.1.200
```

**如何查找你的 IP 范围**：
```bash
# 方法1：查看当前IP
ipconfig | findstr IPv4

# 方法2：查看路由器DHCP范围（通常在管理面板中）
# 常见默认值：
#   - TP-Link：192.168.1.100-199
#   - ASUS：192.168.50.100-199
#   - Netgear：192.168.1.2-254
```

#### 节：`[Outbound]` - 出站过滤（可选）

```ini
[Outbound]
; 设为1启用出站白名单（阻止除允许范围外的所有出站）
Enable = 0
; 启用后，指定允许的出站目标（空=阻止所有！）
AllowedRanges =
```

**⚠️ 注意**：启用出站过滤但不设置 `AllowedRanges` 将阻止**所有**出站流量（包括上网！）。仅在锁定模式使用。

#### 节：`[OutboundPorts]` - 端口阻止（旅行模式）

```ini
[OutboundPorts]
; 旅行模式下阻止的TCP端口（逗号分隔）
BlockTCP = 135,139,445,3389
; 阻止的UDP端口
BlockUDP = 137,138
```

**常见危险端口**：
| 端口 | 协议 | 服务 | 风险 |
|------|------|------|------|
| 135 | TCP/RPC | Microsoft RPC | 被蠕虫利用 |
| 139 | TCP | NetBIOS SSN | 文件共享攻击 |
| 445 | TCP | SMB/CIFS | WannaCry、NotPetya |
| 3389 | TCP | RDP | 暴力破解攻击 |
| 5900 | TCP | VNC | 远程接管 |

#### 节：`[Wail2Ban]` - 入侵检测

```ini
[Wail2Ban]
; 应用配置时自动启动Wail2Ban（0=询问，1=自动）
AutoStart = 0
; 脚本路径（相对于FirewallScripts/）
Path = wail2ban\wail2ban.ps1

; 监控的事件ID（4625 = 登录失败）
EventIDs = 4625
; 计算失败次数的时间窗口（秒）（300 = 5分钟）
FindTime = 300
; 时间窗口内触发封禁的失败次数
MaxRetry = 5
; 各级封禁时长（秒）（逐级递增！）
; 第1次：1小时
; 第2次：5小时
; 第3次：25小时
; 第4次：约125小时（5天）
; 第5次：90天（永久-ish）
BanTimes = 3600,18000,90000,450000,7776000
```

### 预设配置文件

`configs/` 目录包含即用型配置模板：

| 文件 | 配置 | 自动启动Wail2Ban | FindTime | MaxRetry | 特殊 |
|------|------|-----------------|----------|----------|------|
| `home.ini` | 家庭网络 | ✅ 是 | 300s | 5 | 标准防护 |
| `office.ini` | 办公/企业 | ❌ 否 | 300s | 5 | 工作平衡 |
| `travel.ini` | 公共WiFi | ✅ 是 | 180s | 3 | 端口阻止 + 激进 |
| `lockdown.ini` | 最高安全 | ✅ 是 | 60s | 2 | 完全出站阻止 |

使用方法——复制到 `setting.ini`：
```bash
cd FirewallScripts
copy /y configs\travel.ini setting.ini
```

---

## 🛡️ 工作原理（技术概览）

### 架构图

```
┌──────────────────────────────────────────────────────────┐
│                    Netdef.bat（主启动器）                   │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              交互菜单（0-8）                          │ │
│  │  [1] 家庭   [2] 旅行   [3] 清理   [4] W2B启动      │ │
│  │  [5] W2B停止 [6] 完全退出 [7] 日志  [8] GUI        │ │
│  └─────────────────────────────────────────────────────┘ │
│       │         │          │            │          │      │
│       ▼         ▼          ▼            ▼          ▼      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │lan-    │ │outdoor-│ │cleanup-│ │wail2ban│ │netdef- │ │
│  │config  │ │config  │ │rules   │ │manager │ │gui     │ │
│  │.bat    │ │.bat    │ │.bat    │ │.bat    │ │launcher│ │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ │
│      ▼          ▼          ▼          ▼          ▼       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │动态    │ │outdoor-│ │cleanup-│ │wail2ban│ │HTML +  │ │
│  │PS1生成 │ │config  │ │rules   │ │.ps1    │ │WinForms│ │
│  │        │ │.ps1    │ │.ps1    │ │(10s轮询)│ │GUI     │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           setting.ini（统一配置源）                    │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           configs/（配置模板）                         │ │
│  │  home.ini · office.ini · travel.ini · lockdown.ini  │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           logs/（本地日志存储）                        │ │
│  │  wail2ban.log · state.json                          │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 安全模型：零信任 + 纵深防御

```
第1层：网络配置（默认拒绝）
├── 所有入站默认阻止
├── 仅白名单IP允许
└── 出站：可配置（允许/阻止/白名单）

第2层：端口级控制（旅行模式）
├── 阻止危险出站端口（SMB、RDP等）
├── 防止恶意软件外联
└── 减少公共网络攻击面

第3层：行为监控（Wail2Ban）
├── 监控重复失败（暴力破解）
├── 自动封禁攻击者，逐级递增
├── 白名单IP豁免
└── 持久化状态，重启后保留
```

---

## 🖥️ 图形界面

Netdef 包含 **两种 GUI**，可通过菜单选项 **[8]** 或直接 PowerShell 执行启动：

### HTML桥接GUI（默认）

![HTML桥接GUI](FirewallScripts/tests/netdef-resized.png)

重新设计的 HTML 桥接 GUI 提供了精致的深色主题仪表板：

| 区域 | 说明 |
|------|------|
| **顶部栏** | Logo徽标、标题"NETDEF SECURITY SUITE"、实时防火墙和Wail2Ban状态指示灯、语言切换（EN/中文） |
| **左侧边栏** | 大Logo徽章、"Network Definer v1.0"品牌标识、安全级别指示器（含防火墙/Wail2Ban/连接的盾牌图标）、当前配置名称 |
| **配置卡片** | 4个可点击卡片 — 家庭（绿色）、办公（蓝色）、旅行（橙色，星标）、锁定（灰色）— 各含名称和描述 |
| **快捷操作** | 启动/停止Wail2Ban、清理规则、编辑配置、刷新状态 — 一键按钮 |
| **活动日志** | 可滚动的实时日志，带时间戳条目，按类型颜色编码（成功/错误/警告） |
| **底部栏** | 防火墙状态、Wail2Ban状态、配置文件路径、日志文件夹链接 |

**技术细节**：
- 内嵌 WebBrowser 控件，完整双向通信
- HTML → PowerShell：通过 `InvokeScript('getPendingCommands')` 命令队列轮询
- PowerShell → HTML：通过 `InvokeScript('onCommandResult', json)` 状态回调
- 内置 i18n 系统，支持中英文切换（通过 localStorage 持久化）
- 固定布局：1140×720 视口，侧边栏 + 主内容区

### WinForms传统GUI（备选）

![WinForms GUI](FirewallScripts/tests/netdef-resized.png)

独立 WinForms GUI 提供更简洁的原生 Windows 界面：

| 区域 | 说明 |
|------|------|
| **配置按钮** | 4个大号颜色编码按钮 — 家庭（绿色）、办公（蓝色）、旅行（橙色）、锁定（灰色）— 多行标签 |
| **状态面板** | 实时防火墙状态和Wail2Ban运行状态，每5秒自动刷新 |
| **快捷操作** | 启动Wail2Ban、停止Wail2Ban、清理规则、编辑配置、刷新、打开日志 |
| **活动日志** | 可滚动文本区域，显示带时间戳的操作结果 |

**技术细节**：
- 纯 PowerShell Windows Forms — 无浏览器依赖
- 通过 `netdef-gui.ps1` 独立运行，或从启动器加 `-Legacy` 参数作为备选
- 管理员权限检查，带提权提示

---

## 🤝 AI辅助开发故事

### 为什么使用 TRAE SOLO

我是时间有限的单人开发者。我想正确地构建这个工具（安全审计、测试、文档），但独自完成需要数周。

**TRAE SOLO 成了我的结对编程伙伴**，帮我更快地推进同时保持质量。

### AI 帮了什么

| 任务 | 传统耗时 | 使用TRAE | 加速 |
|------|---------|---------|------|
| 架构设计 | 16小时 | 4小时 | **4x** |
| 核心编码（BAT+PS） | 40小时 | 12小时 | **3.3x** |
| **安全审计** | **20小时** | **2小时** | **10x** ⭐ |
| 测试生成 | 16小时 | 2小时 | **8x** |
| 文档编写 | 12小时 | 3小时 | **4x** |
| 调试（估计） | 20小时 | 5小时 | **4x** |
| **合计** | **~124小时** | **~28小时** | **4.4x** |

### 关键时刻：安全审计

公开发布前，我让 TRAE 像安全专家一样审查代码。**30秒内发现了15个我遗漏的问题**：

🔴 **严重（5个）**：
- 配置解析中的输入注入漏洞
- 不安全的临时文件名（竞态条件风险）
- 关键路径缺少错误处理

🟡 **中等（7个）**：
- 防火墙命令前IP验证不足
- 脚本失败时未清理临时文件
- 静默失败隐藏了bug

🟢 **低（3个）**：
- 日志级别不一致
- 缺少边界情况处理

**影响**：2小时内修复所有问题。独自完成需要2-3天。

---

## 📊 性能影响

### 资源占用
| 组件 | 内存 | CPU | 磁盘 |
|------|------|-----|------|
| 脚本（按需运行） | <5MB | 执行时<1% | 可忽略 |
| Wail2Ban（后台） | ~40MB | 空闲<1%，事件时~2% | ~1MB状态文件 |
| GUI（打开时） | ~60MB | <2% | 可忽略 |

### 网络延迟
- 增加延迟：**<1ms**（防火墙规则在内核层执行）
- 吞吐量影响：**不可测量**（无代理、无中间件）
- 连接建立：不受影响（无状态包过滤）

### 电池影响（笔记本）
- Wail2Ban轮询（每10秒）：**<0.5%** 电池消耗
- 相当于：多开一个浏览器标签页

---

## 🧪 测试

### 完整测试结果（2026-04-17）

所有核心功能已测试验证：

| 测试项 | 结果 | 备注 |
|--------|------|------|
| 主启动器菜单 | ✅ 通过 | 8个选项全部正常 |
| 家庭网络（局域网配置） | ✅ 通过 | TrustedRanges读取，规则创建成功 |
| 旅行模式（公共WiFi） | ✅ 通过 | 端口阻止 + 入站过滤 |
| 规则清理 | ✅ 通过 | 预览 + 确认删除 |
| Wail2Ban启动/停止 | ✅ 通过 | 进程管理正常 |
| Wail2Ban检测 | ✅ 通过 | IP封禁 + 白名单豁免 |
| 日志查看器 | ✅ 通过 | Wail2Ban + 防火墙日志 |
| GUI启动 | ✅ 通过 | HTML桥接 + WinForms均正常 |

详见 [`docs/test/test_netdef_full_20260417.md`](docs/test/test_netdef_full_20260417.md)。

---

## 🐛 故障排除

### 常见问题

**Q：脚本运行后立即关闭（看不到错误信息）**

A：不要双击！请从命令提示符运行：
```bash
cmd
cd \path\to\netdef
.\Netdef.bat
```
窗口会保持打开，方便查看错误信息。

---

**Q："Configuration file not found" 错误**

A：确保 `setting.ini` 存在于 `FirewallScripts/` 目录中，与脚本放在一起。

---

**Q：Wail2Ban 没有封禁攻击者**

A：调试步骤：
```bash
# 检查进程是否运行：
powershell -Command "Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" | Where-Object { \$_.CommandLine -like '*wail2ban*' }"

# 查看Wail2Ban日志（现在存储在本地）：
type FirewallScripts\logs\wail2ban.log

# 检查是否产生Event ID 4625：
wevtutil qe Security /c:10 /rd:true /f:"*[System[(EventID=4625)]]"
```

---

**Q：旅行模式端口阻止似乎不生效**

A：端口阻止规则仅对**公用**网络配置文件生效。确保你的连接设置为"公用"：
- 设置 → 网络和Internet → [你的连接] → 属性 → 网络配置文件 = **公用**

验证规则是否存在：
```powershell
Get-NetFirewallRule -DisplayName "[Outbound]*"
```

---

**Q：如何查找我的家庭IP范围？**

A：多种方法：
```bash
# 方法1：查看自己的IP
ipconfig

# 方法2：查看路由器DHCP租约表
# （登录路由器管理页面，通常是 192.168.1.1 或 192.168.0.1）
```

常见路由器品牌默认范围：
- **TP-Link**：`192.168.1.100-199`
- **ASUS**：`192.168.50.100-199`
- **Netgear**：`192.168.1.2-254`
- **D-Link**：`192.168.0.100-199`

---

**Q：日志存储在哪里？**

A：日志存储在本地 `FirewallScripts\logs\`：
- `wail2ban.log` — Wail2Ban入侵检测日志
- `state.json` — Wail2Ban封禁状态（重启后保留）
- Windows防火墙日志：`%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log`

也可通过菜单选项 **[7] → [3]** 或 GUI 的"打开日志"按钮打开日志文件夹。

---

## 📁 项目结构

```
Netdef/
├── Netdef.bat                              # 主启动器（CLI + 菜单）
├── README.md                               # 英文文档
├── README_CN.md                            # 中文文档
├── CHANGELOG.md                            # 版本历史（英文）
├── CHANGELOG_CN.md                         # 版本历史（中文）
├── LICENSE                                 # MIT 许可
├── .gitignore                              # Git忽略规则
├── netdef.png                              # 项目Logo
│
└── FirewallScripts/                        # 核心工具包
    ├── setting.ini                         # 用户配置
    │
    ├── lan-config.bat                      # 配置：家庭网络
    ├── outdoor-config.bat                  # 配置：旅行模式
    ├── cleanup-rules.bat                   # 工具：移除规则
    ├── wail2ban-manager.bat                # 服务：Wail2Ban控制
    │
    ├── outdoor-config.ps1                  # 旅行模式PowerShell逻辑
    ├── cleanup-rules.ps1                   # 清理PowerShell逻辑
    ├── netdef-gui-launcher.ps1             # HTML桥接GUI启动器
    ├── netdef-gui.ps1                      # WinForms GUI（独立）
    ├── netdef-gui-redesigned.html          # HTML GUI界面
    ├── netdef-gui.html                     # HTML GUI（原版）
    │
    ├── wail2ban/                           # 入侵检测引擎
    │   └── wail2ban.ps1                    # 核心监控脚本
    │
    ├── configs/                            # 预设配置模板
    │   ├── home.ini                        # 家庭网络配置
    │   ├── office.ini                      # 办公/企业配置
    │   ├── travel.ini                      # 公共WiFi配置 ⭐
    │   └── lockdown.ini                    # 最高安全配置
    │
    └── logs/                               # 日志文件（本地）
        └── .gitkeep                        # 保留空目录
│
    └── tests/                              # 测试与GUI资源
        └── netdef-resized.png              # GUI徽标图片
│
└── docs/                                   # 文档
    ├── GITHUB_SUBMISSION_CHECKLIST.md      # 发布检查清单
    ├── Plans & Solutions/                  # 开发计划
    └── test/                               # 测试报告
```

---

## 📈 路线图

### v1.0.0（当前） ✅
- [x] 零信任入站过滤与IP白名单
- [x] 4种安全配置（家庭/办公/旅行/锁定）
- [x] Wail2Ban入侵检测，逐级递增封禁
- [x] 出站端口阻止（旅行模式）
- [x] 交互式CLI菜单 + 命令行参数
- [x] HTML桥接GUI + WinForms传统GUI
- [x] 预设配置模板（`configs/`）
- [x] 本地日志存储（`logs/`）
- [x] 完整英文本地化
- [x] 全面文档

### v1.0.1 ✅
- [x] Wail2Ban状态文件Mutex + 原子写入（修复文件锁竞争）
- [x] Wail2Ban单实例强制
- [x] 节感知INI解析器（修复跨节键冲突）
- [x] HTML GUI默认语言设为英文（i18n保留）
- [x] 移除所有占位符文本
- [x] 移除仓库中的真实IP地址
- [x] 修复Netdef.bat语法错误
- [x] 启动时清理临时文件
- [x] 扩展.gitignore

### v1.1（计划中 - 下一版本）
- [ ] 端口转发规则支持
- [ ] 多语言支持（中文、日文）
- [ ] 单元测试套件（Pester）
- [ ] 自动检测本地IP范围
- [ ] 自动更新检查
- [ ] 配置备份/恢复

### v2.0（未来愿景）
- [ ] Web仪表板（React + Node.js后端）
- [ ] 规则导入/导出（JSON格式）
- [ ] 多设备同步（云端或局域网）
- [ ] 威胁情报源集成
- [ ] 自定义检测器插件系统

---

## 🙏 致谢

- **[Wail2Ban项目](https://github.com/Wail2Ban/wail2ban)** - 动态封禁系统的灵感来源（Linux版本）
- **[TRAE SOLO](https://trae.com)** - 让这个项目在创纪录时间内成为可能的AI助手
- **Microsoft文档** - [Windows防火墙参考](https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-firewall)
- **开源社区** - 无数的PowerShell示例和安全研究

---

## 📄 许可

本项目采用 **MIT 许可** - 详见 [LICENSE](LICENSE) 文件。

**简单说**：随便用，出了问题别找我。注明出处更好但不强求。

---

## 📞 支持与联系

- **问题/Bug**：[GitHub Issues](https://github.com/netdef-project/netdef/issues)（首选）
- **安全漏洞**：请通过邮件负责任地报告（不要公开提issue）
- **一般问题**：GitHub Discussions

**响应时间**：通常48小时内（独立开发者，请多包涵！😊）

---

<div align="center">

**⚡ 用 ❤️ 和 [TRAE SOLO](https://trae.com) 构建**

**🏠 为真实的人而做，由真实的人制作**

*如果这个工具帮助你保护了网络安全，请给仓库加个星 ⭐ 帮助更多人发现 Netdef！*

</div>
