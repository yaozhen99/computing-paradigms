# Puck 任务清单 — 2026-04-23 下午

> 派发者：Atlas
> 时间：16:12
> 优先级：高

---

## 任务一：DT 组重构监督

**目标**：监督 DT 组前 4 个插件重构完成

| 插件 | 重构内容 | 状态 |
|------|----------|------|
| parse_json | 添加 `_fail()`、日志改为 `%s`、definition 改 behavior | 待派发 |
| dict_to_list | 同上 | 待派发 |
| list_to_dict | 同上 | 待派发 |
| filter_dict_list | 同上 | 待派发 |

**模范参考**：`C:\civibbs\pipeline\done\aggregate_results\execute.py`

**派发方式**：spawn Claude Code 子代理，按 aggregate_results 模式重构

---

## 任务二：ML 组开发启动

**目标**：启动 ML 组（邮件操作）9 个插件开发

| # | 插件 | 触发机状态 | 开发状态 |
|---|------|-----------|----------|
| 1 | atomic_take | ✅ 已有 | 待派发 |
| 2 | atomic_write | ❌ 缺 | 待派发 |
| 3 | create_agent_mailbox | ❌ 缺 | 待派发 |
| 4 | create_public_mailbox | ❌ 缺 | 待派发 |
| 5 | resolve_mail_target | ❌ 缺 | 待派发 |
| 6 | wait_for_mail_arrival | ❌ 缺 | 待派发 |
| 7 | create_topo_storage_with_copies | ❌ 缺 | 待派发 |
| 8 | create_multiple_topo_units | ❌ 缺 | 待派发 |
| 9 | send_shutdown_to_topo_unit | ❌ 缺 | 待派发 |

**开发规范**：
- 按 aggregate_results 模范代码标准
- 必须包含 `_fail()` 统一出口
- 日志使用惰性格式 `%s`
- definition.yaml 用 `logic.behavior` 契约

**派发顺序**：atomic_take → atomic_write → 其他

---

## 任务三：DT 组归档监督

**目标**：确保 DT 组所有参与者写总结并归档

**需要总结的人**：
- 开发者（Claude Code 子代理）
- 审核者（Athena）

**归档位置**：
- `C:\tower-of-babel\chronicle\dt-group-evaluation-2026-04-23.md`（已完成）
- 各插件 `review.md`（已完成）

**待完成**：
- 开发者总结（开发心得、踩坑经验）
- 归档确认（所有文件移到正确位置）

---

## 执行顺序

1. **立即**：派发 parse_json 重构
2. **并行**：派发 atomic_take 开发
3. **跟进**：监督重构进度，逐个派发剩余插件
4. **收尾**：确认归档完成

---

*派发者：Atlas 🏛️*
*时间：2026-04-23 16:12*