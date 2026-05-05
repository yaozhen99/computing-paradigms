# AI智能体网页聊天操作工具 - 开发需求书

## 一、项目目标

为AI智能体（Hermes Agent）开发一个可直接操作网页聊天的工具，使智能体能像人一样在网页聊天界面读取消息和输入回复。

核心定位：**智能体的手脚**，不是通用爬虫，不是RPA框架。

---

## 二、运行环境

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 |
| 浏览器 | Microsoft Edge（Chromium内核） |
| Python | 3.12+ |
| 执行方式 | 从WSL2通过 `/mnt/c/Python312/python.exe` 调用 |
| 依赖 | Playwright |

---

## 三、核心功能

### 3.1 浏览器连接

**需求**：连接已打开的Edge浏览器实例，共享登录状态。

**方式**：
- Edge以 `--remote-debugging-port=9222` 启动
- 工具通过CDP协议连接
- 自动检测9222端口是否可用，不可用则提示

**接口**：
```
python webchat.py connect
```

**输出**：
```
OK|已连接，当前页面: https://chat.deepseek.com/
FAIL|连接失败，请确认Edge已用--remote-debugging-port=9222启动
```

### 3.2 页面结构探测

**需求**：分析当前页面的DOM结构，自动识别聊天区域和输入框。

**识别逻辑**：
- 输入框：`textarea`、`[contenteditable="true"]`、`input[type="text"]`
- 消息区域：包含对话文本的容器，通过类名关键词（message/chat/conversation/assistant/user）定位
- 输出每个候选元素的标签、类名、ID、placeholder

**接口**：
```
python webchat.py dump
```

**输出**：JSON格式
```json
{
  "url": "https://chat.deepseek.com/",
  "inputs": [
    {"tag": "TEXTAREA", "id": "chat-input", "className": "...", "placeholder": "给DeepSeek发消息"}
  ],
  "message_containers": [
    {"tag": "DIV", "className": "...", "role": "assistant", "text_preview": "你好！有什么..."}
  ]
}
```

### 3.3 消息读取

**需求**：读取当前对话的所有消息，区分角色（用户/AI）。

**接口**：
```
python webchat.py read
python webchat.py read --last    # 只读最后一条
python webchat.py read --since 5  # 读取最近5秒内的新消息
```

**输出**：JSON格式
```json
{
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
  ]
}
```

### 3.4 消息发送

**需求**：在输入框中拟人化输入文本并发送。

**拟人化规则**：
- 逐字输入，每字间隔40-120ms随机
- 标点后额外停顿200-500ms
- 3%概率插入0.5-1.5s的思考停顿
- 发送前停顿300-800ms
- 模拟Enter键发送

**接口**：
```
python webchat.py send "你好，请介绍一下你自己"
```

**输出**：
```
OK|已发送
FAIL|未找到输入框
```

### 3.5 回复等待

**需求**：发送消息后等待AI回复完成。

**检测逻辑**：
- 检测"停止生成"按钮消失
- 检测加载/输入指示器消失
- 连续2秒无新内容则判定回复完成

**接口**：
```
python webchat.py wait [--timeout 120]
```

**输出**：
```json
{"role": "assistant", "content": "回复内容..."}
```
或超时：
```
TIMEOUT|等待超时120秒
```

---

## 四、平台适配

### 4.1 适配层设计

不同聊天网站的DOM结构不同，用配置文件适配：

```json
{
  "deepseek": {
    "url_pattern": "deepseek.com",
    "input_selector": "textarea#chat-input",
    "message_selector": ".dad65929",
    "user_role_indicator": ".user-message",
    "assistant_role_indicator": ".assistant-message",
    "generating_indicator": "button[aria-label*='stop']"
  },
  "chatgpt": {
    "url_pattern": "chatgpt.com",
    "input_selector": "#prompt-textarea",
    "message_selector": "[data-message-author-role]",
    "generating_indicator": "button[aria-label*='Stop']"
  }
}
```

### 4.2 自动探测

如果当前URL没有匹配的配置，自动执行dump逻辑，尝试识别输入框和消息区域。

---

## 五、调用方式

工具从WSL通过Windows Python调用：

```bash
# 连接检查
/mnt/c/Python312/python.exe webchat.py connect

# 探测页面
/mnt/c/Python312/python.exe webchat.py dump

# 读取消息
/mnt/c/Python312/python.exe webchat.py read

# 发送消息
/mnt/c/Python312/python.exe webchat.py send "你好"

# 等待回复
/mnt/c/Python312/python.exe webchat.py wait

# 一条龙：发送+等待回复
/mnt/c/Python312/python.exe webchat.py chat "你好"
```

---

## 七、对话触发机制

> **状态：搁置** — V1 不实现触发器引擎。Hermes 可通过自身的 cron + skill 组合实现等效功能。
> 触发器配置文件和引擎代码保留在 `triggers/` 目录作为占位，待 V2 视需求启用。

### 7.1 触发器设计

工具不只是被动读写，必须支持**自动触发对话**——满足条件时自动发起聊天。

**触发类型**：

| 触发类型 | 说明 | 示例 |
|---------|------|------|
| 定时触发 | 每隔N秒/分钟主动发消息 | 每30分钟问一次"有新进展吗" |
| 事件触发 | 检测到页面变化时触发 | 对方回复了、新消息出现 |
| 条件触发 | 消息内容匹配关键词时触发 | 检测到"完成"/"失败"等关键词 |
| 链式触发 | 上一个对话完成后自动发起下一个 | 对方回答后根据回答追问 |

### 7.2 触发配置

```json
{
  "triggers": [
    {
      "name": "poll_status",
      "type": "timer",
      "interval_seconds": 1800,
      "message": "当前任务进展如何？",
      "enabled": true
    },
    {
      "name": "on_reply",
      "type": "event",
      "event": "new_message",
      "filter": {"role": "assistant"},
      "action": "notify"
    },
    {
      "name": "on_keyword",
      "type": "condition",
      "match": ["完成", "失败", "错误", "成功"],
      "action": "notify_and_log"
    },
    {
      "name": "follow_up",
      "type": "chain",
      "after": "send",
      "wait_reply": true,
      "then": "wait"
    }
  ]
}
```

### 7.3 触发接口

```bash
# 启动监控（后台运行，按触发器配置自动执行）
python webchat.py monitor --config triggers.json

# 停止监控
python webchat.py monitor --stop

# 查看监控状态
python webchat.py monitor --status
```

### 7.4 监控输出

触发器触发时，输出到stdout和日志文件：

```
[2026-05-03 23:45:00] [trigger:poll_status] 定时触发，发送: "当前任务进展如何？"
[2026-05-03 23:45:08] [reply] assistant: "测试已完成，3个通过1个失败"
[2026-05-03 23:45:08] [trigger:on_keyword] 命中关键词"失败"，执行notify_and_log
```

### 7.5 单次对话流程

最常用的场景——发一条消息，等回复，拿结果：

```bash
python webchat.py chat "请分析这段代码的问题" --timeout 120
```

等价于：send → wait → 输出回复内容

**输出**：
```json
{
  "sent": "请分析这段代码的问题",
  "reply": "这段代码有以下问题：1. ...",
  "duration_seconds": 15.3,
  "triggered": []
}
```

---

## 八、异常处理

### 8.1 连接异常

| 异常 | 处理 |
|------|------|
| CDP端口不可达 | 输出FAIL+提示启动命令，不重试 |
| 浏览器崩溃 | 输出FAIL+错误信息，不自动重启 |
| 页面导航失败 | 重试1次，仍失败则输出FAIL |
| 登录态失效 | 输出WARN+提示重新登录 |

### 8.2 操作异常

| 异常 | 处理 |
|------|------|
| 找不到输入框 | 输出FAIL，建议先dump探测 |
| 发送后无回复 | 等到timeout，输出TIMEOUT |
| 回复中断（部分生成） | 输出已有内容+标记incomplete:true |
| 输入框被清空/失焦 | 重新定位，重试1次 |

### 8.3 反检测异常

| 异常 | 处理 |
|------|------|
| 出现验证码/CAPTCHA | 输出BLOCK+截图保存，暂停操作 |
| 账号被限制提示 | 输出BLOCK+停止所有操作 |
| 频率限制提示 | 自动等待60秒后重试，最多3次 |

---

## 九、安全约束

### 9.1 账号安全

- 不存储明文密码
- 登录态（cookie）加密存储在auth/目录
- cookie文件权限仅当前用户可读
- 每次连接前检查cookie有效期

### 9.2 操作安全

- 发送前可配置确认模式（--confirm，需手动确认才发送）
- 单次对话最大发送次数限制（默认20次/小时）
- 单条消息最大长度限制（默认4000字符）
- 不自动点击页面上的非聊天元素（广告、链接等）

### 9.3 数据安全

- 对话记录仅存储在本地
- 日志文件不包含cookie/token
- 支持对话记录自动清理（默认保留7天）

---

## 十、测试验收标准

### 10.1 基础功能验收

| 编号 | 测试项 | 通过标准 |
|------|--------|---------|
| T01 | 连接浏览器 | connect命令返回OK，识别到已打开页面 |
| T02 | 页面探测 | dump命令返回输入框和消息区域的正确选择器 |
| T03 | 读取消息 | read命令返回当前对话的所有消息，角色区分正确 |
| T04 | 发送消息 | send命令成功输入文本并发送，打字速度在40-120ms/字 |
| T05 | 等待回复 | wait命令正确检测回复完成，返回完整回复内容 |
| T06 | 一条龙对话 | chat命令完成发送+等待+返回，端到端可用 |

### 10.2 触发机制验收

| 编号 | 测试项 | 通过标准 |
|------|--------|---------|
| T07 | 定时触发 | 配置30秒间隔，30秒后自动发送消息 |
| T08 | 事件触发 | 对方回复后，触发器正确识别并执行action |
| T09 | 关键词触发 | 回复包含配置的关键词时，触发器正确命中 |
| T10 | 链式触发 | 发送后自动等待回复，回复后可配置后续动作 |

### 10.3 异常处理验收

| 编号 | 测试项 | 通过标准 |
|------|--------|---------|
| T11 | 无浏览器 | connect返回FAIL+提示，不崩溃 |
| T12 | 无输入框 | send返回FAIL+建议dump，不崩溃 |
| T13 | 回复超时 | wait返回TIMEOUT，不卡死 |
| T14 | 验证码拦截 | 检测到CAPTCHA返回BLOCK+截图，不继续操作 |

### 10.4 拟人化验收

| 编号 | 测试项 | 通过标准 |
|------|--------|---------|
| T15 | 打字速度 | 每字40-120ms，标点后有停顿 |
| T16 | 随机性 | 连续发送3次相同文本，每次总耗时不同 |
| T17 | 思考停顿 | 100字以上输入至少出现1次0.5s+停顿 |

---

## 十一、文件结构

> **项目位置**：`C:\tower-of-babel\hermes\webchat\`（Hermes 团队工作目录下，非 CiviBBS）

```
C:\tower-of-babel\hermes\webchat\
  webchat.py              # 主入口，命令行接口
  adapters/               # 平台适配配置
    __init__.py            # 适配器加载器
    deepseek.json
    chatgpt.json
    zhipu.json
  lib/
    __init__.py
    browser.py             # 浏览器连接管理
    reader.py              # 消息读取
    writer.py              # 拟人化输入
    detector.py            # 回复完成检测
    dumper.py              # 页面结构探测
  auth/                    # 登录状态存储（预留）
  triggers/                # 触发器配置（V2）
  logs/                    # 对话日志
  REQ.md                   # 本文档
```
