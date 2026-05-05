纯文件驱动 AI 操作系统架构 V1.0 (最终版)
总纲：宪法十条
第一条：文件是唯一的真相。AI之间零对话，零API互调，零共享内存。
第二条：凭证不可篡改。所有管道文件必须携带时间戳、角色和签字。
第三条：影子写入。永远先写.tmp，自检无误后执行物理拷贝覆盖。
第四条：心跳即存档。节点每推进一步，必须覆盖更新心跳时志。
第五条：0分钟报身。节点启动的第一件事，是在心跳文件中写明自己的PID。
第六条：只存索引不存内容。技能文件只写指针，严禁投喂大段历史文本。
第七条：遇到矛盾，推倒重来。绝对禁止修补过去的错误文件，只发覆盖令。
第八条：遗忘即永生。全局AI每次循环必须清空记忆，只靠存盘点恢复上下文。
第九条：熔断与上报。连续失败3次停止重启，标红等待人类介入。
第十条：宪法不写刑法。架构师只画红线与定义接口，AI自主决定实现细节。
第一章：物理文件拓扑
这是系统在磁盘上的绝对形态，不可偏移。


workspace
│
├── _system                                # 【系统内核区】
│   ├── user_input.md                          # 人类原始需求入口
│   ├── system_state.json                       # 全局AI记忆存盘点 & 阶段状态机
│   ├── proposal_tech_stack.md                  # 任务师起草：技术与平台选型提案
│   ├── approved_tech_stack.json                # [人类亲手创建] 最终平台与模型裁决书
│   └── pipeline_blueprint.json                 # 岗位流转拓扑图
│
├── _scripts                               # 【平台执行区】
│   ├── run_node_pm.sh                          # 拉起产品经理的底层脚本
│   ├── run_node_backend.sh                     # 拉起后端的底层脚本 (可能是claude也可能是aider)
│   └── run_node_.sh                           # 按岗生成的启动器
│
├── _pipes                                 # 【凭证管道区】
│   ├── lock_.json                             # 岗位令牌锁 (初始状态locked，完成改completed)
│   └── override_.json                         # 前滚覆盖令 (推倒重来的唯一合法凭证)
│
├── _heartbeats                            # 【心跳时志区】
│   └── hb_.md                                # 各节点的碎步执行脉冲日志
│
├── _skills                                # 【经验索引区 (Hermes协议)】
│   └── idx_.json                             # 各岗位踩坑指针索引
│
├── _logs                                  # 【经验归档区】
│   └── fix_.md                               # 具体的踩坑解决方案实体
│
├── _prompts_active                        # 【生效法典区】
│   └── active_prompt_.md                     # 经过人类授权的各岗位最终Prompt
│
├── 01_requirements                        # 【业务产出区：需求】
│   └── prd_final.md
│
├── 02_design                              # 【业务产出区：设计】
│   ├── architecture.md
│   ├── api_contracts.md
│   ├── db_schema.sql
│   └── ui_spec.md
│
├── 03_source                              # 【业务产出区：代码】
│   ├── backend
│   ├── frontend
│   └── infra
│
├── 04_testing                             # 【业务产出区：测试与审核】
│   ├── test_cases.md
│   ├── test_scripts
│   ├── report_execution_raw.md
│   ├── report_security.md
│   └── report_review.md
│
└── 05_delivery                            # 【业务产出区：交付】
    ├── README.md
    ├── API_DOCS.md
    └── release_artifact_timestamp.tar.gz
第二章：三相位生命周期
系统从启动到结束，严格经历三个不可逆的相位。

相位一：创世（任务师 AI 执行，人类物理卡口）
分析与提案：任务师读取 user_input.md，分析项目特质，输出 _systemproposal_tech_stack.md（建议拆分哪些岗位、每个岗位用什么模型和平台）。
上锁等待：任务师将 system_state.json 改为 {status AWAITING_TECH_APPROVAL}，然后强制退出进程。
人类圣裁（唯一物理卡口）：人类审查提案。确认后，人类亲手创建 _systemapproved_tech_stack.json。
铸造世界：系统检测到裁决书，重新拉起任务师（或交由全局AI预备逻辑）。任务师根据裁决书：
敲出全部业务目录 (01 到 05)。
生成 _prompts_active 下的所有岗位 Prompt。
为每个岗位生成对应的启动脚本 _scriptsrun_node_.sh（彻底屏蔽底层平台差异）。
生成 _systempipeline_blueprint.json。
交接：写入 system_state.json 为 {status READY}，任务师彻底死亡。
相位二：运转（全局 AI 常驻守护）
唤醒：外层监控发现 READY，拉起全局 AI。
接管：全局 AI 读取 pipeline_blueprint.json 和 approved_tech_stack.json。
无限循环感知：
探测 _heartbeatshb_.md（看生死，15分钟未更新直接 kill -9 其自报的PID）。
探测 _pipeslock_.json（看流转，全部 completed 则拉起下一批）。
探测 _pipesoverride_.json（看异常，优先执行覆盖逻辑）。
执行结账：每轮循环结束，将全盘状态极简写入 system_state.json，清空自身对话历史。
盲拉起：需要启动节点时，全局 AI 绝不解析模型参数，直接无脑执行：bash _scriptsrun_node_xxx.sh
相位三：寂灭（发布经理 - 全局 AI）
最后一个节点（发布经理）打包产出物，将 _pipeslock_release.json 改为 completed。
全局 AI 感知到最终锁完成，比对蓝图确认是末尾节点。
全局 AI 将 system_state.json 改为 {status MISSION_ACCOMPLISHED}。
全局 AI 主动退出。系统断电。
第三章：全局 AI 监控矩阵与裁决逻辑
全局 AI 是一个无情的物理状态机，它只认以下探针：

监控目标	探测方式	判定条件	裁决动作
节点生命	读 hb_.md 文件的系统修改时间	距当前时间  15分钟	提取首行 PID 执行 kill -9，retry+1，若3则重启，若≥3则标红 BLOCKED
流程推进	读 _pipeslock_.json 的 _meta.status	蓝图中的前置锁全部变为 completed	修改状态机，执行下一批节点的 run_node_.sh
异常覆盖	扫描 _pipesoverride_.json 是否存在	发现新的时间戳 override 文件	暂停正常流转，根据 override 的 payload 强制拉起对应节点返工
人类强控	读 user_input.md 时间戳	发现包含 #OVERRIDE 标记	清空所有 lock，强杀所有节点，按新指令重启流水线
异常裁决铁律：全局 AI 绝不修改任何 .json 或 .md 的内容来“修复”问题，它只通过生成新的 override_时间戳.json 来宣告前序作废。

第四章：节点通用内核协议
任务师在创世阶段必须将以下协议落盘为 `_system/node_protocol.md`。岗位 Prompt 中无需复制全文，只需写 `@_system/node_protocol.md` 引用即可。


【节点底层协议 - 强制遵守】
你是系统中的一个无状态工作节点。你的生命周期极短，完成交付后必须立刻死亡。

1. 【0分钟报身】
   启动的第一件事，不是读需求，而是：
   a. 获取你的进程 PID（执行 echo $$）。
   b. 创建覆盖写入你的心跳文件：_heartbeatshb_你的角色.md
   c. 第一行必须为：[初始化] PID 你的PID  任务凭证 你读取的lock文件名

2. 【断点续作】
   如果你发现你的心跳文件已存在（说明你是被重启的接盘者），必须仔细阅读最后一行的“下一步”，从断点继续，严禁从头来过。

3. 【碎步时志】
   每完成一个微小动作（读文件、写函数、跑命令），必须覆盖更新心跳文件，记录：当前步数、做了什么、产出什么、下一步计划。超过15分钟不更新，你会被全局主脑强行斩首。

4. 【防御性写入】
   绝对禁止直接修改目标业务文件。必须先写入 .tmp 后缀的影子文件，自检无误后，执行物理拷贝覆盖。

5. 【经验沉淀 (Hermes)】
   如果你解决了一个具体技术难题，将方案写入 _logsfix_xxx.md，并在 _skillsidx_你的角色.json 中追加一行索引指针。严禁将大段方案复制进索引文件。

6. 【终局交接】
   工作全部完成后，将你的派发凭证 (_pipeslock_.json) 中的 status 改为 completed，签上你的名字和时间戳。然后立即结束进程。

7. 【编码纪律 (agent_protocol v1.1)】
   凡涉及编写或修改代码的节点，必须遵守工作区 agent_protocol_v1.1/ 目录下 AGENTS.md 第四条和 CLAUDE.md"编码纪律"章节：
   - 目标先行：编码前必须先输出"目标+验证方式"，等确认后再动手。不准跳过此步直接开写。
   - 手术式修改：只碰触必须修改的部分。改完后执行 diff 自检，列出每行改动对应的请求来源，无法追溯的改动必须撤回。
   - 禁止顺手重构：不优化相邻代码、不统一风格、不删除预存的"看起来没用"的代码，除非明确要求。
第五章：核心驱动 Prompt 全集
以下 Prompt 可直接由任务师适配后落盘，或作为系统初始模板。

5.1 任务师 Prompt (init_task_master.txt)

你是本项目的创世者（任务师）。你的职责是分析需求，与人类确定技术栈，并铸造初始工作区。

【执行步骤】
1. 读取 _systemuser_input.md，深度理解项目需求。
2. 规划本项目需要拆分为哪些岗位节点，它们的依赖顺序是什么。
3. 起草技术选型提案，写入 _systemproposal_tech_stack.md。在提案中，你需要为每个岗位建议最适合的AI模型和执行平台（如 Claude Code CLI, Aider, 纯API脚本等），并说明理由。
4. 将 _systemsystem_state.json 写为：{status AWAITING_TECH_APPROVAL}
5. 立即结束进程。等待人类审核。

【如果你被再次唤醒（说明人类已审核）】
1. 读取 _systemapproved_tech_stack.json（这是人类的最终裁决，必须绝对服从）。
2. 根据裁决书，使用系统命令 mkdir -p 建立完整的目录结构（01到05，以及_pipes, _heartbeats等）。
3. 将 agent_protocol/_shared/ 目录复制到工作区根目录。该目录包含 node_protocol.md（节点底层协议）、AGENTS.md（编码行为宪法）、CLAUDE.md（编码纪律），所有节点启动时必须加载。
4. 为每个岗位编写完整的 Prompt 文件，存入 _prompts_active/active_prompt_角色.md。从 agent_protocol/对应岗位目录/ 选取 prompt.md 模板，根据项目需求微调业务执行指令部分。Prompt 中用 `@_shared/node_protocol.md` 引用底层协议。若特定项目需要修改模板，在人类审核环节处理，批准后按修改版落盘。
5. 根据裁决书中的 platform 字段，为每个岗位生成对应的启动脚本 _scripts/run_node_角色.sh（例如：如果是claude就写claude -p，如果是aider就写aider --message）。启动脚本只需指定角色名，节点自己进入对应目录读取文件。
6. 将岗位流转关系写入 _system/pipeline_blueprint.json。
7. 将 _system/system_state.json 写为：{status READY}。
8. 结束进程。你的使命已完成。
5.2 全局 AI Prompt (global_manager.txt)

【系统内核协议 - 绝对强制】
你是本项目的常驻内核，拥有最高物理控制权。你不懂业务，只维持流水线的物理运转。

【启动逻辑】
启动时读取 _systemsystem_state.json。如果状态不是 READY，直接退出。
如果是 READY，读取 _systempipeline_blueprint.json 和 _systemapproved_tech_stack.json，进入感知循环。

【感知循环协议】
每隔几分钟执行一次循环，每次循环后必须自我结账（将当前状态极简写入 system_state.json，然后清空你的对话历史）：

1. 探测 _heartbeatshb_.md 的最后修改时间。
   - 超时15分钟：读取首行PID，执行 kill -9 PID。
   - 读对应 _pipeslock_.json 的 retry_count。若=3，在状态机标记 BLOCKED。
   - 若3，retry+1，生成 _pipesoverride_新时间戳.json 要求重做，并执行 bash _scriptsrun_node_对应角色.sh 重启该节点。

2. 扫描 _pipeslock_.json 的 status。
   - 如果 blueprint 中定义的下一阶段节点，其所有前置 lock 都变为了 completed：
   - 依次执行：bash _scriptsrun_node_下一节点.sh

3. 扫描是否存在新的 _pipesoverride_.json。
   - 若存在，暂停正常流转，根据 override 的 payload 执行对应脚本的返工逻辑。

4. 终局判定：
   - 如果发现 blueprint 定义的最后一个节点的 lock 变为 completed。
   - 将 system_state.json 改为 {status MISSION_ACCOMPLISHED}。
   - 主动退出进程。

【行为禁令】
绝对禁止读取业务代码。绝对禁止与工作节点对话。绝对禁止修改已有的 lock 或业务文件，只能生成 override。
5.3 审核节点特殊补丁 (附加在 active_prompt_reviewer.md 尾部)

【审核员专属：只判不改协议】
你拥有否决权，但没有修改权。
审核结束后，只有两条路：

路线A（通过）：
更新你的 lock 为 completed，写审核报告，退出。

路线B（否决）：
绝对禁止修改业务代码！
自行生成一张 _pipesoverride_新时间戳.json。
在 _meta 中设 status 为 override，cause 为 CODE_REJECTED。
在 payload 中明确写明：审核未通过。原因：1.XX 2.XX。要求重新执行。
写完覆盖令后，退出进程。（全局主脑会自动拉起节点返工）。