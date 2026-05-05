[返工开始] 2026-05-03T23:45:00+08:00 角色 tester_write 返工任务
- 触发：审核员指出测试未覆盖"文件删除失败"场景的退出码验证
- 返工内容：
  1. 补充 TC-CLI-26: lock 命令原文件删除失败返回 GENERAL_ERROR (1) 而非 CRYPTO_ERROR (3)
  2. 补充 TC-CLI-27: unlock 命令 .vault 文件删除失败返回 GENERAL_ERROR (1) 而非 CRYPTO_ERROR (3)
- 状态：进行中
