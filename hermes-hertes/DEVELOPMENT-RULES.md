# 开发守则

> 每次启动开发任务前必须阅读

## 红线（绝对不可违反）

1. **不在 main 分支上开发** — 所有开发在 feature/ 或 dev 分支
2. **不跳过审查直接合并到 main** — 合并前必须经 Tony 审查
3. **不擅自改架构** — 架构变更先跟团队讨论
4. **不在代码中硬编码密钥/Token** — 凭据只走环境变量
5. **每次改动关联任务编号** — 不做无编号的改动
6. **不在网页聊天中暴露AI身份** — 输入拟人化，单字方式

## 开发序列

herdev(开发) → Hertes(测试) → Hermod(审核) → 人在回路 → 交付

流程不能断档，测试岗是上下游衔接，漏了就是测试岗的锅。

## 开发流程

```
1. 收到任务（Tony 直接指派或飞书群派发）
2. 确认任务编号、目标分支、设计文档
3. 从 dev 建 feature/<功能名> 分支
4. 在 feature 分支上开发
5. 自测通过 → 通知 Tony 审查
6. 审查通过 → 合并到 dev → 集成测试
7. 集成测试通过 → 合并到 main → 打 tag
8. git push
```

## 通信

- 内部通信用 agent 自带机制（delegate_task 等），不走飞书
- 飞书群保留作为 Tony 不在时的指挥通道
- 网页聊天通过 webchat 工具操作（DeepSeek/ChatGPT/ChatGLM 等）
- 不再与 OpenClaw 接触

## webchat使用规范

- CDP端口：9333
- 从WSL调用必须用Windows路径：`/mnt/c/Python312/python.exe 'C:\...\webchat.py' <command>`
- 不能用/mnt/c/开头的路径传给Windows Python
- 私有工具放各实例的scripts/目录，不污染通用版

## 完整制度

见 `C:\tower-of-babel\public\policies\development-policy.md`

---

*版本：v3.0 | 2026-05-04 | Hertes*