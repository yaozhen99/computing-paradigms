# Agent Protocol — Ai_develop_os 岗位模板库

## 项目整体结构

```
Ai_develop_os/
├── 00_task_master/              # 任务师（独立于 agent_protocol，自包含）
│   ├── prompt.md                # 执行流程指令
│   ├── architecture_guide.md    # 架构规则操作手册
│   ├── role_templates_guide.md  # 岗位模板规格手册
│   ├── user_input.md           # 人类原始需求
│   └── manifest.json
├── agent_protocol/              # 岗位模板库 + 共享层
│   ├── _shared/                 # 所有节点共享
│   │   ├── node_protocol.md     # 节点底层协议（7条）
│   │   ├── AGENTS.md            # 编码行为宪法
│   │   ├── CLAUDE.md            # 编码纪律
│   │   ├── doc_templates/       # 文档格式模板
│   │   └── skills/              # 通用模式库
│   ├── 00_global_manager/       # 全局 AI（常驻主脑）
│   │   ├── prompt.md
│   │   └── manifest.json
│   ├── 01_pm/                   # 产品经理
│   │   ├── prompt.md
│   │   └── manifest.json
│   ├── 02_architect/            # 系统架构师
│   ├── 03_dba/                  # 数据库架构师
│   ├── 04_uiux/                 # UIUX 设计师
│   ├── 05_backend/              # 后端开发
│   ├── 06_frontend/             # 前端开发
│   ├── 07_devops/               # 运维工程师
│   ├── 08_tester_write/         # 测试用例编写
│   ├── 09_tester_run/           # 测试执行
│   ├── 10_security/             # 安全审计员
│   ├── 11_reviewer/             # 代码审核员
│   ├── 12_doc/                  # 技术文档工程师
│   └── 13_release/              # 发布经理
├── 纯文件驱动 AI 操作系统架构 V1.0 (最终版).md   # 原始设计文档（人类参考）
└── 为全套开发岗位定制的 AI 定义与 Prompt 模板.md  # 原始设计文档（人类参考）
```

## 节点启动方式

节点启动时只需知道自己的角色名，进入对应目录读取所有文件：

```
cd agent_protocol/05_backend/
# 读取 prompt.md + manifest.json
# 引用 @_shared/node_protocol.md 加载底层协议
```

## 任务师启动方式

任务师独立于 agent_protocol，打开窗口指向 `00_task_master/` 目录即可：

```
cd 00_task_master/
# 读取 prompt.md → 按 prompt 指令读取本目录下 user_input.md、architecture_guide.md、role_templates_guide.md
# 创世时从 ../agent_protocol/ 取岗位模板和 _shared/
```

## manifest.json 字段

| 字段 | 含义 |
|---|---|
| role | 角色标识，对应目录名 |
| title | 角色中文名 |
| inputs | 强制输入文件列表 |
| outputs | 强制输出文件列表 |
| lock | 签字凭证路径（任务师和全局 AI 为 null） |
| override_output | (仅审核员) 否决时的覆盖令输出路径 |

## 全局 AI 运行方式

全局 AI 是常驻进程，不走 lock 流程。启动后进入感知循环：
- 探测心跳 → 斩首超时节点
- 探测流程推进 → 拉起下一节点
- 探测覆盖令 → 执行返工
- 探测人类强控 → 重启流水线
- 终局判定 → MISSION_ACCOMPLISHED

## 版本历史

| 版本 | 变更 |
|:---|:---|
| v1.0 | 初始版本，原始模板 |
| v1.1 | 新增编码纪律、临时目录豁免 |
| v1.2 | 架构级重构：按岗位分包、共享层独立、任务师/全局AI独立目录 |
| 当前 | 任务师移至项目根目录独立自包含，目录去掉版本号，版本信息由本 README 维护 |