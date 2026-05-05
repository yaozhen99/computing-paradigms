# CiviBBS L1 插件开发任务清单

> 每个插件 = 一个任务 = definition.yaml定义 + execute.py实现 + 触发机验证 + 测试通过
> 优先级：fs > dt > ml > cf > lg > pt > bb（基础通用 → 业务特定）
> 每个任务需要：开发 → 测试 → 审核，可能走多遍流程

## fs — 文件系统（10个）🔥 最基础，最优先

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 1 | L1-FS-001 | read_file | ✅ normal/file_not_found | 待开发 |
| 2 | L1-FS-002 | write_file | ❌ | 待开发 |
| 3 | L1-FS-003 | copy_file | ❌ | 待开发 |
| 4 | L1-FS-004 | move_file | ❌ | 待开发 |
| 5 | L1-FS-005 | delete_file | ❌ | 待开发 |
| 6 | L1-FS-006 | file_exists | ❌ | 待开发 |
| 7 | L1-FS-007 | list_files | ❌ | 待开发 |
| 8 | L1-FS-008 | get_file_info | ❌ | 待开发 |
| 9 | L1-FS-009 | create_directory | ✅ normal/already_exists/no_permission | 待开发 |
| 10 | L1-FS-010 | delete_directory | ❌ | 待开发 |

## dt — 数据转换（7个）🔥 通用基础

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 11 | L1-DT-001 | parse_json | ❌ | 待开发 |
| 12 | L1-DT-002 | dict_to_list | ❌ | 待开发 |
| 13 | L1-DT-003 | list_to_dict | ❌ | 待开发 |
| 14 | L1-DT-004 | filter_dict_list | ❌ | 待开发 |
| 15 | L1-DT-005 | update_dict_list | ❌ | 待开发 |
| 16 | L1-DT-006 | ensure_dict_fields | ❌ | 待开发 |
| 17 | L1-DT-007 | aggregate_results | ❌ | 待开发 |

## ml — 邮件操作（9个）🔥 邮件总线核心

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 18 | L1-ML-001 | atomic_take | ✅ normal/empty_inbox | 待开发 |
| 19 | L1-ML-002 | atomic_write | ❌ | 待开发 |
| 20 | L1-ML-003 | create_agent_mailbox | ❌ | 待开发 |
| 21 | L1-ML-004 | create_public_mailbox | ❌ | 待开发 |
| 22 | L1-ML-005 | resolve_mail_target | ❌ | 待开发 |
| 23 | L1-ML-006 | wait_for_mail_arrival | ❌ | 待开发 |
| 24 | L1-ML-007 | create_topo_storage_with_copies | ❌ | 待开发 |
| 25 | L1-ML-008 | create_multiple_topo_units | ❌ | 待开发 |
| 26 | L1-ML-009 | send_shutdown_to_topo_unit | ❌ | 待开发 |

## cf — 配置文件（2个）

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 27 | L1-CF-001 | read_config_file | ❌ | 待开发 |
| 28 | L1-CF-002 | validate_config | ❌ | 待开发 |

## lg — 日志（3个）

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 29 | L1-LG-001 | init_logger | ❌ | 待开发 |
| 30 | L1-LG-002 | log_error | ❌ | 待开发 |
| 31 | L1-LG-003 | log_exit_reason | ❌ | 待开发 |

## pt — 进程/线程（18个）

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 32 | L1-PT-001 | generate_id | ❌ | 待开发 |
| 33 | L1-PT-002 | parse_signal | ❌ | 待开发 |
| 34 | L1-PT-003 | create_exit_event | ❌ | 待开发 |
| 35 | L1-PT-004 | register_signal_handlers | ❌ | 待开发 |
| 36 | L1-PT-005 | start_thread | ❌ | 待开发 |
| 37 | L1-PT-006 | check_thread_alive | ❌ | 待开发 |
| 38 | L1-PT-007 | stop_process | ❌ | 待开发 |
| 39 | L1-PT-008 | cancel_timeout_tasks | ❌ | 待开发 |
| 40 | L1-PT-009 | filter_tasks_by_status | ❌ | 待开发 |
| 41 | L1-PT-010 | read_task_store | ❌ | 待开发 |
| 42 | L1-PT-011 | pause_ac_task_accept | ❌ | 待开发 |
| 43 | L1-PT-012 | wait_for_exit_signal | ❌ | 待开发 |
| 44 | L1-PT-013 | wait_for_tasks_completion | ❌ | 待开发 |
| 45 | L1-PT-014 | wait_server_stop | ❌ | 待开发 |
| 46 | L1-PT-015 | wait_topo_unit_stop | ❌ | 待开发 |
| 47 | L1-PT-016 | cleanup_temp_files | ❌ | 待开发 |
| 48 | L1-PT-017 | write_shutdown_log | ❌ | 待开发 |
| 49 | L1-PT-018 | write_shutdown_marker | ❌ | 待开发 |

## bb — BBS业务（3个）

| # | 任务ID | 插件名 | 触发机 | 状态 |
|---|--------|--------|--------|------|
| 50 | L1-BB-001 | create_bbs_data_dir | ❌ | 待开发 |
| 51 | L1-BB-002 | load_bbs_templates | ❌ | 待开发 |
| 52 | L1-BB-003 | verify_web_service | ❌ | 待开发 |

---

## 统计
- **总计**：52个任务（51个插件 + 1个预留）
- **有触发机**：3个（read_file, create_directory, atomic_take）
- **缺触发机**：49个
- **优先级排序**：fs(10) → dt(7) → ml(9) → cf(2) → lg(3) → pt(18) → bb(3)

## 每个任务的流程
1. **开发**：按 definition.yaml 实现 execute.py
2. **触发机**：编写触发机 YAML（normal + 异常场景）
3. **测试**：触发机验证通过
4. **审核**：Atlas/Tony 审核代码质量
5. **可能多遍**：审核不通过则返工

---
*生成时间：2026-04-21 23:23*
*生成者：Atlas 🏛️*
