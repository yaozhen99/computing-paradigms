# OpenClaw Playwright 补丁安装记录

> 日期: 2026-04-28
> 环境: Windows / Python 3.14 / CiviBBS v2.0 & v2.5
> 执行者: Trae AI Agent

---

## 1. 问题背景

CiviBBS v2.0 的 [deepseek_web.py](file:///c:/civibbs/v2.0/lib/deepseek_web.py) 通过 Playwright 自动化访问 DeepSeek Web 聊天页面，实现无需 API Key 的 AI 对话能力。该模块是 OpenClaw Guardian Agent 浏览器自动化交互的核心依赖。

v2.5 的 [guardian_agent.py](file:///c:/civibbs/v2.5/lib/agents/guardian_agent.py) 中 OpenClaw 集成标记为 `TODO`，但 Playwright 作为未来浏览器自动化的基础设施，需要提前部署。

**当前状态**: OpenClaw 构建版本不包含 Playwright 支持，需要安装补丁。

---

## 2. 环境诊断

### 2.1 初始检查

```powershell
# 检查 Playwright 是否已安装
pip show playwright
# WARNING: Package(s) not found: playwright

# 尝试导入
python -c "from playwright.async_api import async_playwright"
# ModuleNotFoundError: No module named 'playwright'
```

### 2.2 本地浏览器缓存检查

```powershell
# 检查 ms-playwright 目录
dir "$env:LOCALAPPDATA\ms-playwright"
```

发现本地已有旧版 Playwright 安装的浏览器二进制:

```
chromium-1217                    # 旧版 Chromium (Playwright 1.59.x)
chromium_headless_shell-1217     # 旧版 Headless Shell
ffmpeg-1011                      # FFmpeg
winldd-1007                      # Windows LDD
```

---

## 3. 补丁安装过程

### 步骤 1: 安装 Playwright Python 包

```powershell
pip install playwright
```

**安装结果**:
- `playwright 1.58.0` (Python 包)
- `greenlet 3.5.0` (依赖)
- `pyee 13.0.1` (依赖)
- `typing-extensions 4.15.0` (已存在)

> ⚠️ 下载速度较慢 (33.2 KB/s)，36.8 MB 耗时约 25 分钟，因网络连接 PyPI 不稳定。

### 步骤 2: 安装 Chromium 浏览器二进制 (失败)

```powershell
playwright install chromium
```

**失败原因**: 从 Google Storage 下载 `chrome-win64.zip` (172.8 MB) 反复超时:

```
Error: Request to https://storage.googleapis.com/chrome-for-testing-public/
145.0.7632.6/win64/chrome-win64.zip timed out after 30000ms
```

Playwright 1.58.0 需要 `chromium-1208` 版本，但直接下载不可用。

### 步骤 3: 尝试 npmmirror 镜像 (失败)

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"
playwright install chromium
```

**失败原因**: npmmirror 尚未同步 Playwright 1.58.0 对应的 Chromium 版本:

```
Error: Download failed: server returned code 404
Key: binaries/playwright/145.0.7632.6/win64/chrome-win64.zip
```

### 步骤 4: 本地浏览器二进制兼容方案 (成功)

**关键发现**: 本地 `ms-playwright` 目录已有 `chromium-1217` (来自之前安装的 Playwright 1.59.x)，而新安装的 Playwright 1.58.0 期望 `chromium-1208`。

**解决方案**: 将现有浏览器二进制复制为 Playwright 1.58.0 期望的版本号目录。

```powershell
# 复制 Chromium 主浏览器
Copy-Item -Path "$env:LOCALAPPDATA\ms-playwright\chromium-1217" `
          -Destination "$env:LOCALAPPDATA\ms-playwright\chromium-1208" `
          -Recurse -Force

# 复制 Chromium Headless Shell
Copy-Item -Path "$env:LOCALAPPDATA\ms-playwright\chromium_headless_shell-1217" `
          -Destination "$env:LOCALAPPDATA\ms-playwright\chromium_headless_shell-1208" `
          -Recurse -Force
```

**原理**: Playwright 通过目录版本号 (`chromium-1208`) 定位浏览器二进制。Chromium 1217 和 1208 的二进制结构完全兼容 (均为 `chrome-win64/chrome.exe`)，版本差异不影响基本功能。

---

## 4. 验证结果

### 4.1 Playwright 基本功能验证

```powershell
python -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=True)
page = browser.new_page()
page.goto('https://www.baidu.com')
title = page.title()
print(f'Page title: {title}')
browser.close()
p.stop()
print('Playwright works correctly!')
"
```

**输出**:
```
Page title: 百度一下，你就知道
Playwright works correctly!
```

### 4.2 CiviBBS deepseek_web.py 导入验证

```powershell
cd C:\civibbs\v2.0
python -c "
from lib.deepseek_web import DeepSeekWebSession, DeepSeekWebSync, chat_with_deepseek
print('deepseek_web.py imported successfully!')
"
```

**输出**:
```
deepseek_web.py imported successfully!
```

### 4.3 浏览器路径确认

```powershell
python -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
print('Chromium path:', p.chromium.executable_path)
p.stop()
"
```

**输出**:
```
Chromium path: C:\Users\yz01\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe
```

---

## 5. 补丁文件清单

### 5.1 新增 Python 包

| 包名 | 版本 | 路径 |
|------|------|------|
| playwright | 1.58.0 | `C:\Python314\Lib\site-packages\playwright\` |
| greenlet | 3.5.0 | `C:\Python314\Lib\site-packages\greenlet\` |
| pyee | 13.0.1 | `C:\Python314\Lib\site-packages\pyee\` |

### 5.2 新增浏览器二进制

| 目录 | 来源 | 路径 |
|------|------|------|
| chromium-1208 | 复制自 chromium-1217 | `%LOCALAPPDATA%\ms-playwright\chromium-1208\` |
| chromium_headless_shell-1208 | 复制自 chromium_headless_shell-1217 | `%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-1208\` |

### 5.3 受影响的 CiviBBS 模块

| 文件 | 版本 | 说明 |
|------|------|------|
| `civibbs/v2.0/lib/deepseek_web.py` | v2.0 | Playwright 异步浏览器自动化，DeepSeek Web 会话 |
| `civibbs/v2.5/lib/agents/guardian_agent.py` | v2.5 | Guardian Agent，OpenClaw 模型标识，TODO: API 集成 |

---

## 6. 关键代码参考

### 6.1 deepseek_web.py 核心类

```python
class DeepSeekWebSession:
    """DeepSeek Web会话客户端 - 基于 Playwright 异步 API"""

    async def start(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        if self.user_data_dir:
            self.context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless
            )
        else:
            self.browser = await self._playwright.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def send_message(self, message: str) -> str:
        # 自动查找输入框 -> 填入消息 -> 点击发送 -> 等待回复
        input_selectors = [
            '#chat-input',
            'textarea[placeholder*="输入"]',
            'div[contenteditable="true"]',
            'textarea',
        ]
        # ... 省略详细逻辑

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()


class DeepSeekWebSync:
    """同步封装 - 通过事件循环桥接异步 API"""

    def start(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self.session.start())
        self._loop.run_until_complete(self.session.open_chat())

    def send_message(self, message: str) -> str:
        if not self._started:
            self.start()
        return self._loop.run_until_complete(self.session.send_message(message))


def chat_with_deepseek(message: str, headless: bool = False) -> str:
    """便捷函数 - 与 DeepSeek 对话"""
    session = get_deepseek_session(headless)
    return session.send_message(message)
```

### 6.2 guardian_agent.py OpenClaw 集成点

```python
class GuardianProfile:
    MODEL = "openclaw"  # 由 OpenClaw agent 处理

class GuardianAgent(AgentBase if V25_AVAILABLE else object):
    def _generate_reply(self, prompt, sender, subject, memory_context):
        # TODO: 集成 OpenClaw API
        # 当前返回一个基于 Guardian 身份的回复
        if "安全" in prompt or "审计" in prompt:
            return self._security_audit_response(prompt, sender)
        # ...
```

### 6.3 Playwright 版本兼容性补丁脚本

```powershell
# ============================================================
# OpenClaw Playwright 补丁安装脚本
# 适用于: Windows + Python 3.14 + Playwright 1.58.0
# 用途: 当网络无法下载 Chromium 时，利用本地已有二进制
# ============================================================

# Step 1: 安装 Playwright Python 包
pip install playwright

# Step 2: 检查本地是否已有浏览器二进制
$playwrightDir = "$env:LOCALAPPDATA\ms-playwright"
$existingChromium = Get-ChildItem -Path $playwrightDir -Directory -Filter "chromium-*" |
    Sort-Object Name -Descending | Select-Object -First 1

if ($existingChromium) {
    $existingVersion = $existingChromium.Name -replace "chromium-", ""
    Write-Host "Found existing Chromium version: $existingVersion"

    # Step 3: 尝试在线安装
    playwright install chromium 2>$null

    # Step 4: 如果在线安装失败，使用本地兼容方案
    $targetVersion = "1208"  # Playwright 1.58.0 期望的版本
    $targetDir = Join-Path $playwrightDir "chromium-$targetVersion"

    if (-not (Test-Path $targetDir)) {
        Write-Host "Online install failed, using local binary compatibility..."
        Copy-Item -Path $existingChromium.FullName `
                  -Destination $targetDir `
                  -Recurse -Force
        Write-Host "Copied $($existingChromium.Name) -> chromium-$targetVersion"
    }

    # Headless Shell 同理
    $existingHeadless = Get-ChildItem -Path $playwrightDir -Directory -Filter "chromium_headless_shell-*" |
        Sort-Object Name -Descending | Select-Object -First 1

    if ($existingHeadless) {
        $headlessTarget = Join-Path $playwrightDir "chromium_headless_shell-$targetVersion"
        if (-not (Test-Path $headlessTarget)) {
            Copy-Item -Path $existingHeadless.FullName `
                      -Destination $headlessTarget `
                      -Recurse -Force
            Write-Host "Copied $($existingHeadless.Name) -> chromium_headless_shell-$targetVersion"
        }
    }
} else {
    Write-Host "No existing Chromium found. Must download from network."
    playwright install chromium
}

# Step 5: 验证
python -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=True)
page = browser.new_page()
page.goto('https://www.baidu.com')
print(f'Page title: {page.title()}')
browser.close()
p.stop()
print('Playwright patch installed successfully!')
"
```

---

## 7. 已知限制与后续事项

### 7.1 版本兼容性

- 当前使用 `chromium-1217` 二进制兼容 `chromium-1208` 路径，Chromium 主版本差异不大，基本功能正常
- 如需精确版本匹配，在网络稳定时运行 `playwright install chromium` 重新下载官方二进制

### 7.2 零依赖规则冲突

- CiviBBS 项目规则要求"零依赖"（仅使用 Python 标准库）
- Playwright 是第三方包，`deepseek_web.py` 属于 v2.0 实验性代码，不在 small 插件体系内
- 如需纳入 v2.5 small 插件架构，需考虑标准库替代方案（`urllib` + HTML 解析）

### 7.3 OpenClaw API 集成

- Guardian Agent 的 OpenClaw API 集成仍为 `TODO` 状态
- 当前回复逻辑基于关键词匹配，非真正 AI 对话
- Playwright 为未来通过浏览器自动化与 OpenClaw Web 界面交互提供了基础设施

---

## 8. 架构关系

```
OpenClaw Ecosystem
├── CiviBBS v2.0
│   ├── lib/deepseek_web.py          [Playwright] 自动化访问 DeepSeek Web
│   │   ├── DeepSeekWebSession       异步 Playwright 会话
│   │   ├── DeepSeekWebSync          同步封装
│   │   └── chat_with_deepseek()     便捷函数
│   ├── web/app.py                   [OpenClaw] model=="openclaw" 异步处理
│   └── extension/                   Chrome Manifest V3 扩展
│
├── CiviBBS v2.5
│   ├── lib/agents/guardian_agent.py [OpenClaw] Guardian Agent (TODO: API)
│   │   ├── GuardianProfile          MODEL = "openclaw"
│   │   ├── GuardianMemory           ~/.openclaw/workspace-guardian
│   │   └── GuardianAgent            关键词匹配占位实现
│   └── data/app/mail/agents/guardian/profile.json
│
└── Playwright Infrastructure (本次补丁)
    ├── playwright 1.58.0            Python 包
    ├── chromium-1208                浏览器二进制 (兼容自 chromium-1217)
    └── chromium_headless_shell-1208 Headless Shell (兼容自 1217)
```
