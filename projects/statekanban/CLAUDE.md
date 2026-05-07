# StateKanban 项目守则

## 项目状态
- 当前轮次：R4（接口修正 + 真实 API 验证）
- 运行模式：V2 Agent
- R1/R2/R3 已完成，R3 Reviewer 发现 11 个 issues，其中接口偏差需修正
- 代码基座：05_delivery/statekanban/（R3 产出）

## 代码位置
- 所有可运行代码在 `05_delivery/statekanban/`
- 测试代码在 `04_testing/test_scripts/`
- 设计文档在 `02_design/`

## R4 需求概览（3 REQ）
- REQ-401：set_behavior_mode 双参数签名修正（mock_adapter.py）
- REQ-402：E2E 测试改 Engine.drive() 驱动（test_e2e.py）
- REQ-403：真实 API 烟雾测试（test_live_api.py 新增，conftest.py 改）

## 关键约束
- 底座零 I/O：引擎不直接写文件，所有写出通过阀门
- 修正必须向后兼容（R3 的 369+ 测试仍通过）
- 真实 API 测试标记 `@pytest.mark.live_api`，需 `--run-live` 才执行
- 不改核心模块接口

## 验收标准（4 条）
1. 全部测试通过（369+ + 新增），无 skip 无 xfail
2. set_behavior_mode("reviewer", "strict") 双参数签名可调用
3. E2E 测试由 Engine.drive() 驱动，非手动组装
4. `pytest --run-live` 可执行真实 API 烟雾测试（需 ANTHROPIC_API_KEY）

## 开发纪律
- Python 3.11+，使用 black 格式化
- 测试框架：pytest
- 错误码体系：SK_XX_NNN（见 core/errors.py）