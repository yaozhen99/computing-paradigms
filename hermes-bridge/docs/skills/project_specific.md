# Hermes Bridge 项目专属技能库

> 本文件记录与**本项目特定架构、业务规则、模块依赖**相关的经验、踩坑和最佳实践。

## 1. 架构约定
- **双向通信架构**：Claude Code ←MCP→ Hermes Bridge (8898) ←WSL→ Hermes
- **端口固定**：Bridge 服务固定使用端口 8898
- **数据存储**：所有任务、结果、消息均使用 JSON 文件持久化到 filesystem

## 2. 业务规则
- **任务 ID 生成**：优先使用请求中的 `task_id`，否则生成 uuid 前 8 位
- **消息推送**：Hermes 通过 `POST /message` 推送，写入 `inbox/` 目录
- **结果查询**：支持 `GET /result` 列出全部，或 `GET /result/<id>` 查询单个

## 3. 模块依赖关系
- `bridge.py` → `mcp_server.py`：MCP Server 依赖 Bridge 的 HTTP 端点
- `bridge.py` → WSL/Hermes CLI：通过 `wsl -d Alpine-WSL1 -e sh -c` 调用 Hermes

## 4. 常见踩坑记录
### WSL 路径转义问题
- **现象**：Hermes CLI 命令执行失败
- **原因**：双引号内的查询字符串需要转义
- **解决方案**：`query.replace('"', '\\"')`

### 原代码 error 变量未定义
- **现象**：NameError at line 58
- **原因**：`error` 变量在异常处理分支外未定义
- **解决方案**：使用 `raw_output` 变量

## 5. 配置与环境相关
- **WSL 环境**：必须安装 Alpine-WSL1 发行版
- **Python 虚拟环境**：Hermes 需要 `source ~/hermes-venv/bin/activate`
- **MCP 配置**：`.mcp.json` 必须指向正确的 `mcp_server.py` 路径

## 更新记录
- **2026-04-23 11:30**：初始化技能库（Hermes Bridge 双向通信开发完成）
