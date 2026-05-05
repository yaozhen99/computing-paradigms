# OpenClaw Gateway B1+B2 补丁文档

> 版本: 1.0.0 | 日期: 2026-05-02 | 适用: OpenClaw 2026.4.26+ / Windows 11

---

## 背景

OpenClaw Gateway 在 Windows 上存在两个系统性问题：

1. **崩溃即死** — Gateway 进程异常退出后无自动恢复机制，Windows 计划任务未注册，服务静默中断
2. **配置损坏无前置校验** — `openclaw.json` 在写入过程中被截断或损坏时，Gateway 启动直接失败。历史记录显示 10 次 `.clobbered.*` 事件（2026-04-20 至 2026-05-01），最小仅 845 bytes（正常 3610 bytes）

---

## B1: 反转崩溃策略 — Gateway 守护重启

### 文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `gateway-watchdog.cmd` | `~/.openclaw/` | 守护脚本，替代直接调用 `gateway.cmd` |

### 行为

```
gateway-watchdog.cmd
  ├── 每次启动前调用 gateway-healthcheck.cmd (B2)
  ├── 调用 gateway.cmd 启动 Gateway
  ├── 监听退出码:
  │   ├── 0  → 正常退出，watchdog 停止
  │   ├── 42 → 请求重启，立即重启（重置计数器）
  │   └── 其他 → 崩溃，指数退避后重启
  └── 退避策略:
      ├── 基础延迟: 2s
      ├── 延迟公式: 2 × 2^(retry-1)，上限 60s
      ├── 重置窗口: 5 分钟无崩溃则计数器归零
      └── 最大重试: 10 次，超出后放弃 (exit 1)
```

### 退避时序示例

| 重试次数 | 等待时间 |
|----------|----------|
| 1 | 4s |
| 2 | 8s |
| 3 | 16s |
| 4 | 32s |
| 5+ | 60s (上限) |

### 日志

- 路径: `~/.openclaw/logs/gateway-watchdog.log`
- 格式: `[日期 时间] 消息`

---

## B2: 配置原子写入保护 — 启动前校验 + last-good 恢复

### 文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `gateway-healthcheck.cmd` | `~/.openclaw/` | 配置校验与恢复脚本 |
| `validate-config.js` | `~/.openclaw/scripts/` | JSON 结构校验 (node) |
| `timestamp.js` | `~/.openclaw/scripts/` | ISO 时间戳生成 (替代已废弃的 wmic) |

### 校验流程

```
gateway-healthcheck.cmd
  ├── Step 1: 文件存在性检查
  │   └── 不存在 → 尝试从 .last-good 或 .bak 恢复
  ├── Step 2: 文件大小检查 (< 64 bytes = 截断)
  │   └── 过小 → recover()
  ├── Step 3: JSON 解析 + 结构校验 (validate-config.js)
  │   ├── 必须包含: models, agents, gateway
  │   └── gateway 必须包含: auth
  │   └── 失败 → recover()
  ├── Step 4: 更新 .last-good (仅当 config 比 last-good 更新时)
  └── 返回: 0 = 健康, 1 = 已恢复

:recover 子流程
  ├── 生成 ISO 时间戳 (timestamp.js)
  ├── 保存损坏配置为 .clobbered.<timestamp>Z
  ├── 优先从 .last-good 恢复
  ├── 备选从 .bak 恢复
  └── 无备份可用 → exit 1
```

### 返回码

| 退出码 | 含义 |
|--------|------|
| 0 | 配置健康（或已成功恢复） |
| 1 | 配置损坏且无法恢复 |

### 日志

- 路径: `~/.openclaw/logs/gateway-healthcheck.log`
- 格式: `[日期 时间] 消息`

---

## Windows 计划任务

### 注册的任务

| 任务名 | 触发器 | 用途 |
|--------|--------|------|
| `OpenClaw Gateway` | 用户登录时 | 主启动入口 |
| `OpenClaw Gateway (Startup)` | 系统启动后 30s | 兜底启动 |

### 注册/更新命令

```powershell
schtasks /Create /TN "OpenClaw Gateway" /TR "C:\Users\yz01\.openclaw\gateway-watchdog.cmd" /SC ONLOGON /RL HIGHEST /F
schtasks /Create /TN "OpenClaw Gateway (Startup)" /TR "C:\Users\yz01\.openclaw\gateway-watchdog.cmd" /SC ONSTART /DELAY 0000:30 /RL HIGHEST /F
```

---

## 完整启动链路

```
Windows 登录/启动
  └── schtasks → gateway-watchdog.cmd
        ├── gateway-healthcheck.cmd (校验 + 恢复)
        │     ├── validate-config.js (JSON 结构校验)
        │     └── timestamp.js (clobbered 时间戳)
        └── gateway.cmd (启动 Gateway 进程)
              └── node openclaw gateway --port 18789
```

---

## 已知约束

1. **cmd.exe 中禁止 `node -e "..."`** — cmd.exe 会截断含分号的引号内代码，必须用独立 `.js` 文件
2. **wmic 已废弃** — Win11 24H2+ 移除了 `wmic`，时间戳改用 `timestamp.js` (node)
3. **退避计时器精度** — 使用 `TIME` 环境变量计算秒数，跨午夜时可能误重置（低影响，最多多一次重试）
4. **计划任务权限** — 需要 HIGHEST 运行级别，用户必须是管理员组成员

---

## 测试记录

| 测试项 | 日期 | 结果 |
|--------|------|------|
| 正常配置校验 | 2026-05-02 | exit 0, "Config OK (3610 bytes)" |
| 截断配置恢复 | 2026-05-02 | exit 1, 检测 10 bytes → 保存 clobbered → 从 .last-good 恢复至 3610 bytes |
| 计划任务注册 | 2026-05-02 | ONLOGON + ONSTART 均注册成功 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-05-02 | 初始版本：B1 守护重启 + B2 配置校验恢复 + Windows 计划任务 |
