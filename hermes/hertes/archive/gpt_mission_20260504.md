# Hertes分身任务指令 — GPT代码评审与补完

## 任务目标

带着CiviBBS两组插件（pt组16个 + lg组3个），去GPT（ChatGPT网页版）对话，完成以下三步：

1. **评审**：让GPT评价每个插件的代码质量和规范完备性，打分（1-10）
2. **补完**：针对GPT提出的意见，要求他给出9分以上的改进代码和扩充规范
3. **测试用例**：要求GPT给出完备的测试用例

## 弹药位置

- pt组（18个插件）: C:\civibbs\pipeline\done_claude\pt\
- lg组（3个插件）: C:\civibbs\pipeline\done_claude\lg\

每组目录下有README.md和每个插件的子目录，每个插件子目录包含：
- definition.yaml — 插件规范
- execute.py — 插件代码
- triggers/（仅lg组）— 触发器配置

## 产出目录

Tony会提前把done_claude的pt和lg两组复制到done_claude_opus2下，分身直接在该目录里更新和新增文件，不需要从零创建目录结构。

基础目录: C:\civibbs\pipeline\done_claude_opus2\
  pt\
    cancel_timeout_tasks\
      definition.yaml      ← 更新
      execute.py           ← 更新
      triggers\            ← 新增测试触发机yaml
      test_cases.md        ← 新增
      review_gpt.txt       ← 新增评审对话记录
    check_thread_alive\
      ...
  lg\
    init_logger\
      definition.yaml      ← 更新
      execute.py           ← 更新
      triggers\            ← 新增测试触发机yaml
      test_cases.md        ← 新增
      review_gpt.txt       ← 新增评审对话记录
    ...

分身操作原则：
- definition.yaml和execute.py：覆盖更新（GPT改进版替换原版）
- triggers/、test_cases.md、review_gpt.txt：新增

## 操作流程

### 阶段一：建立对话

1. 用webchat_new.py在ChatGPT开新对话
2. 用webchat send发送第一条消息，建立上下文

### 阶段二：逐个评审

对每个插件：
1. 读取definition.yaml和execute.py内容
2. 通过webchat chat发给GPT，要求评审
3. 用webchat wait等待GPT回复
4. 用webchat read --last获取评审结果

### 阶段三：要求补完

根据GPT的评审意见：
1. 要求GPT给出9分以上的改进代码
2. 要求GPT给出扩充后的definition.yaml
3. 要求GPT给出完备的测试用例（test_cases.md）
4. 要求GPT给出测试触发机配置（triggers/目录下的yaml）
5. 保存与GPT的完整评审对话为review_gpt.txt

### 阶段四：保存产出

1. 将GPT给出的改进代码、规范、测试用例保存到对应目录
2. 每个插件一个子目录

## 对话策略

- 不暴露自己是AI/智能体身份
- 以开发者身份提问
- **全程用英语与GPT对话**，避免中文乱码和上下文理解偏差
- 必要时用英语改写definition.yaml规范（GPT对英文规范的评审更准确）
- 每次对话聚焦一个插件，避免上下文过长
- 如果GPT回复被截断，用read获取完整内容
- 如果一个对话太长导致质量下降，开新对话继续
- 评审时要求GPT用1-10打分，并逐项给出扣分原因
- 补完时明确要求"at least 9/10 quality"

## webchat调用方式

```bash
# 开新对话
/mnt/c/Python312/python.exe 'C:\tower-of-babel\hermes\hertes\scripts\webchat_new.py'

# 发消息+等回复
/mnt/c/Python312/python.exe 'C:\tower-of-babel\projects\webchat\webchat.py' chat '消息内容' --timeout 120

# 只发不等
/mnt/c/Python312/python.exe 'C:\tower-of-babel\projects\webchat\webchat.py' send '消息内容'

# 等回复
/mnt/c/Python312/python.exe 'C:\tower-of-babel\projects\webchat\webchat.py' wait --timeout 120

# 读最后一条
/mnt/c/Python312/python.exe 'C:\tower-of-babel\projects\webchat\webchat.py' read --last
```

## 插件清单

### pt组（18个）
1. cancel_timeout_tasks
2. check_thread_alive
3. cleanup_temp_files
4. create_exit_event
5. filter_tasks_by_status
6. generate_id
7. parse_signal
8. pause_ac_task_accept
9. read_task_store
10. register_signal_handlers
11. start_thread
12. stop_process
13. wait_for_exit_signal
14. wait_for_tasks_completion
15. wait_server_stop
16. wait_topo_unit_stop
17. write_shutdown_log
18. write_shutdown_marker

### lg组（3个）
1. init_logger
2. log_error
3. log_exit_reason

## 注意事项

- Windows Python只认Windows路径，不认/mnt/c/开头的WSL路径
- 读取文件内容用read_file工具，不要用cat
- 保存产出用write_file工具
- GPT回复可能很长，注意read获取完整内容
- 拟人化输入，不要暴露身份
