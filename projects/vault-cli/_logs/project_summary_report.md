# vault-cli 项目总结报告

**项目名称**：vault-cli — 本地文件加密命令行工具
**项目空间**：C:\tower-of-babel\projects\vault-cli\
**协议版本**：V1（首次实战，V2 协议已基于本次经验完成初稿）
**状态**：MISSION_ACCOMPLISHED

---

## 一、项目目标

开发一个本地文件加密 CLI 工具，支持 `vault init / lock / unlock / list` 四个子命令，使用 AES-256-GCM 加密、PBKDF2-SHA256 密钥派生，零外部服务依赖，离线可用。

---

## 二、流水线执行结果

| 阶段 | 角色 | 状态 | 核心产出 |
|:---|:---|:---|:---|
| 1 | PM | completed | prd_final.md（5 个 User Story + 8 条业务边界） |
| 2 | 架构师 | completed | architecture.md + api_contracts.md（四层架构 + 4 个子命令契约） |
| 3 | 后端开发 | completed | 03_source/backend/（18 个源码文件，完整代码树） |
| 4 | 测试编写 | completed | 94 个测试用例 + 7 个 pytest 脚本 |
| 5 | 测试执行 | completed | 94 passed, 0 failed |
| 6 | 审核员 | completed | report_review.md（首次否决→返工→通过） |
| 7 | 集成 | completed | 05_delivery/（wheel + tar.gz + install.md + changelog + checksums） |

**返工次数**：1 次
**返工原因**：审核员发现文件删除失败时退出码返回 CRYPTO_ERROR(3) 而非契约要求的 GENERAL_ERROR(1)
**返工结果**：后端修复 lock.py/unlock.py，测试补充 TC-CLI-26/27 两个用例，重测 94/94 通过，审核通过

---

## 三、交付物清单

### 可安装交付物（05_delivery/）

| 文件 | 说明 |
|:---|:---|
| vault_cli-1.0.0-py3-none-any.whl | Wheel 包（16,683 字节） |
| vault_cli-1.0.0.tar.gz | 源码分发包（10,175 字节） |
| pyproject.toml | 打包配置（入口: vault = vault_cli.cli.main:main） |
| install.md | 安装说明 |
| changelog.md | 变更日志 v1.0.0 |
| checksums.txt | SHA256 校验和 |

### 源码（03_source/backend/src/vault_cli/）

| 模块 | 文件 | 职责 |
|:---|:---|:---|
| cli/ | main.py, password.py, exit_codes.py | CLI 入口、口令安全输入、退出码枚举 |
| cli/commands/ | init.py, lock.py, unlock.py, list.py | 四个子命令处理 |
| crypto/ | service.py | AES-256-GCM 加解密 |
| keymgr/ | manager.py | PBKDF2-SHA256 密钥派生（600,000 迭代） |
| fileio/ | vault_io.py | .vault 文件读写、原子写入 |
| 根 | errors.py | 8 个异常类 |

### 测试（04_testing/）

| 文件 | 用例数 |
|:---|:---|
| test_crypto_service.py | 15 |
| test_keymgr.py | 14 |
| test_vault_io.py | 18 |
| test_password.py | 6 |
| test_cli_commands.py | 27（含返工补充 2 个） |
| test_e2e_roundtrip.py | 5 |
| test_main_and_errors.py | 9 |
| **合计** | **94** |

### 设计文档

| 文件 | 说明 |
|:---|:---|
| 01_requirements/prd_final.md | 产品需求文档 |
| 02_design/architecture.md | 四层架构设计 |
| 02_design/api_contracts.md | API 契约（4 个子命令 + 错误码） |
| docs/plans/2026-05-03_architecture.md | 开发计划 |
| docs/notes/backend_dev_note.md | 后端开发笔记 |
| docs/summaries/backend_dev_summary.md | 后端开发总结（含差异分析） |

---

## 四、质量指标

| 指标 | 结果 |
|:---|:---|
| 测试通过率 | 100%（94/94） |
| 契约偏差 | 0（返工后 21 个退出码场景全部与契约一致） |
| 安全审查 | 通过（PBKDF2 600K 迭代、AES-256-GCM、getpass 不回显、原子写入、无硬编码凭据） |
| 安装验证 | wheel 包可 pip install |

---

## 五、V1 协议实战发现与 V2 改进

### 发现 1：岗位裁剪误判

V1 裁剪掉了 release 岗位，导致项目"代码写完了但跑不起来"。release 的合成职责（打包交付物）和发布职责（CI/CD 分发）被混为一谈。

**V2 修正**：拆为不可裁剪的 `integration` 阶段 + 可选的 `release` 阶段。铁三角：PM / Reviewer / Integration。

### 发现 2：claude -p 新窗口启动不可靠

V1 设计用 `claude -p` 在新 CMD 窗口启动独立进程，实际执行时节点跑不起来，最终用 Agent 子代理代行。

**V2 修正**：双模式设计。Agent 模式用主会话 + 子代理调度，ISA 模式用 tmux/send-keys 长驻会话。

### 发现 3：文件协调机制在同步调度下冗余

心跳、lock、override 在 Agent 子代理同步调度场景下冗余——子代理返回值就是状态。

**V2 修正**：Agent 模式下 lock 保留但仅用于跨会话恢复，心跳和 override 可选。

### 发现 4：隐含依赖未声明

tester_write 需要读 api_contracts.md（来自架构师），但蓝图中未声明此依赖。

**V2 修正**：蓝图节点必须显式声明 `inputs` 字段，不允许隐含依赖。

### 发现 5：执行过程不可观测

子代理执行时用户看不到实时输出，完成后只返回一个摘要。

**V2 修正**：全局 AI 在每次子代理返回后向 `_logs/pipeline_execution_log.md` 追加记录。

### 发现 6：返工时补丁叠补丁

首次返工时在原有代码上修补，可能导致代码腐化。

**V2 修正**：返工指令强制包含"抛弃半成品，从零重实现"。

---

## 六、待办

- [ ] README.md — 项目使用说明（用户另行编写）
- [ ] V2 协议初稿完善 — 位于 `Ai_develop_os_exc/v2_draft/protocol_v2_draft.md`
- [ ] V2 实战验证 — 用 V2 Agent 模式重新跑一个项目

---

## 七、关键文件索引

| 用途 | 路径 |
|:---|:---|
| 流水线执行日志 | `_logs/pipeline_execution_log.md` |
| 审核否决令 | `_pipes/override_20260503.json` |
| V2 协议初稿 | `Ai_develop_os_exc/v2_draft/protocol_v2_draft.md` |
| V2 Agent 模板 | `Ai_develop_os_exc/agent_protocol/v2_agent/` |
| V2 ISA 模板 | `Ai_develop_os_exc/agent_protocol/v2_isa/` |
| 任务师 V2 prompt | `Ai_develop_os_exc/00_task_master/prompt.md` |