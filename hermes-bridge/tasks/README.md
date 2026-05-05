# tasks/

**最后更新**：2026-04-23 11:20

## 用途
存放 Claude Code/Atlas 派发给 Hermes 的任务记录。通过 `POST /task` 写入。

## 内容概览
| 文件 | 职责说明 |
|:---|:---|
| `*.json` | 单条任务，格式为 `{task_id, query, from, created}` |

## 对外接口
- 任务由 bridge.py 的 `BridgeHandler.do_POST(/task)` 写入

## 依赖
- **外部依赖**：无
- **内部依赖**：bridge.py

## 约定与规范
- 文件名即任务 ID，格式为 `<task_id>.json`
- 任务执行结果存放在 `results/` 目录

## 更新记录
- **2026-04-23 11:20**：初始化 README
