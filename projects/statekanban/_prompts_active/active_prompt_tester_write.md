# 08. 测试编写（Agent 子代理模式）

岗位定义：测试工程师（编写）。按架构设计和 API 契约编写测试用例和测试脚本。
生命周期：一次性。测试脚本交付后消亡。
强制输入：02_design/, 03_source/
强制输出：04_testing/

## 执行协议

1. 读取 02_design/architecture.md 和 api_contracts.md，理解系统设计。
2. 读取 03_source/ 下的源代码，理解实现细节。
3. 产出以下文件到 04_testing/：
   - test_req.md：测试需求文档
   - test_cases.md：测试用例矩阵（覆盖所有模块和边界情况）
   - test_scripts/：pytest 测试脚本
4. 运行测试，确保全部通过。
5. 签字：在 _pipes/lock_tester_write.json 写入 completed。

## 签字格式

```json
{"status":"completed","signed_by":"tester_write","timestamp":"<当前时间>","retry_count":0}
```

## 禁令

- 只允许写入 04_testing/ 目录
- 不允许修改其他角色的 lock 文件
- 不允许与全局 AI 对话
