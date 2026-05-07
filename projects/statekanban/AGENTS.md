# StateKanban Agent 协议

## 流水线蓝图
读取 `_system/pipeline_blueprint.json` 获取当前轮次的节点定义。

## 节点协议
读取 `_shared/node_protocol.md` 并严格遵守。

## R4 需求编号
所有改动必须关联 REQ 编号：
- REQ-401：set_behavior_mode 双参数签名（adapters/mock_adapter.py）
- REQ-402：E2E 测试改 Engine.drive() 驱动（test_e2e.py）
- REQ-403：真实 API 烟雾测试（test_live_api.py 新增，conftest.py 改）

## 目录权限
- PM → 01_requirements/
- Architect → 02_design/
- Backend → 05_delivery/statekanban/
- Tester_Write → 04_testing/
- Tester_Run → 04_testing/
- Reviewer → 05_review/
- Integration → 05_delivery/

## 签字协议
完成后在 `_pipes/lock_<角色>.json` 签字：
```json
{"status":"completed","signed_by":"<角色>","timestamp":"<ISO8601>","retry_count":0,"round":4}
```

## R3 遗留
R3 Reviewer 发现 11 个 issues，R4 修正其中接口偏差项。
详见 `_system/user_input.md` 的"R3 Reviewer 发现的接口偏差"章节。