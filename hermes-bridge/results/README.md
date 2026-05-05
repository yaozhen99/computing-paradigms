# results/

**最后更新**：2026-04-23 11:20

## 用途
存放 Hermes 任务执行结果。由 `run_hermes()` 函数在任务完成后写入。

## 内容概览
| 文件 | 职责说明 |
|:---|:---|
| `*.json` | 单条结果，格式为 `{task_id, status, output, error, returncode, completed}` |

## 对外接口
- 结果由 bridge.py 的 `run_hermes()` 写入
- 由 `BridgeHandler.do_GET(/result)` 列出、`do_GET(/result/<id>)` 查询单条

## 依赖
- **外部依赖**：无
- **内部依赖**：bridge.py、Hermes CLI (WSL)

## 约定与规范
- 文件名即任务 ID，格式为 `<task_id>.json`
- status 字段取值：`running` / `done` / `error` / `timeout`

## 更新记录
- **2026-04-23 11:20**：初始化 README
