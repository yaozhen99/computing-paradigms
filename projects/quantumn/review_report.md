# Quantumn 量化交易系统审核报告

**审核人**: Hermod  
**审核日期**: 2026-05-02  
**审核范围**: quantumn 量化交易系统三个版本（通达信/同花顺/期货）  
**报告路径**: `/mnt/c/tower-of-babel/projects/quantumn/review_report.md`

---

## 一、项目概览

| 维度 | 通达信版 (v0.8) | 同花顺版 (v0.8-ths) | 期货版 (v1.0/v1.01) |
|------|-----------------|---------------------|---------------------|
| **路径** | `/mnt/c/quant_system_v0.8` | `/mnt/c/quant_system_v0.8_ths` | `/mnt/c/quant_futures_v1.0` + `v1.01` |
| **目标平台** | 通达信PC客户端 | 同花顺PC客户端（32位） | 博易云（炒单模式） |
| **交易品种** | A股股票 | A股股票（模拟交易） | 期货（IF/IC/IM等） |
| **执行通道** | 双通道（API + UI自动化） | 仅UI通道 | 仅UI通道 |
| **行情源** | TdxQuant本地接口 | akshare网络接口 | 新浪HTTP + AKShare |
| **数据获取** | UI控件读取 + 导出文件 | UI控件读取（Static/Edit） | 导出文件解析 |
| **核心代码量** | ~5,400行 | ~4,300行 | ~3,700行 |
| **策略示例** | MA均线交叉 | MA均线交叉 | 盘口炒单 |
| **dry-run模式** | 无 | 无 | 有 |

---

## 二、代码质量与架构合理性

### 2.1 整体架构评价：★★★☆☆（3/5）

三个版本共享同一套"管道架构"设计理念：

```
行情 → 策略 → 风控 → 执行器 → 回报更新
```

这一架构思路清晰、模块边界明确，是合理的量化系统骨架。但实现层面存在显著问题。

**优点：**
- 管道式数据流设计合理，Signal → RiskGate → Executor → OrderResult 链路清晰
- 策略基类（Strategy）接口简洁：`initialize` / `on_bar` / `on_order_result` / `finalize`
- 风控闸门（RiskGate）关卡式设计实用：限额 → 频率 → 熔断，且支持手动解除
- 通达信版双通道（API + UI降级）设计有前瞻性
- 期货版支持 `--dry-run` 模式，便于策略调试

**问题：**
- 三个版本大量代码复制粘贴，未做抽象和复用
- 缺少单元测试（通达信版有 `tests/` 目录但内容不明，期货版 v1.01 才开始补 tests）
- 无类型检查配置（mypy），类型注解不完整
- 无 CI/CD、无代码规范配置（black/flake8/pylint）

### 2.2 核心模块逐一评审

#### 2.2.1 main.py — 主循环

**问题等级：中**

三个版本的 `main.py` 结构几乎相同（TradingSystem / FuturesTradingSystem），核心逻辑复制粘贴：

| 问题 | 说明 |
|------|------|
| 重复代码 | `initialize()`、`run()`、`process_signals()`、`_update_by_result()` 三个版本高度雷同 |
| 硬编码 | `SYNC_INTERVAL = 60` 直接写在 run() 里，应提到 config |
| 佣金计算 | `_calc_commission()` 在通达信版和同花顺版完全相同，但各自独立实现 |
| 窗口重连 | 三个版本都有窗口重连逻辑，代码几乎一致但独立维护 |
| 主循环结构 | while True + time.sleep 轮询，无事件驱动，无优雅退出机制（仅 KeyboardInterrupt） |
| 状态日志 | 期货版用 `int(now) % 30 == 0` 做定期日志，不精确且可能跳过 |

#### 2.2.2 executor.py — 执行器

**问题等级：高**

| 问题 | 说明 |
|------|------|
| API通道未完成 | 通达信版 `_cancel_by_api()` 明确标注"暂未实现"，API下单后无法撤单是严重缺陷 |
| 状态不精确 | UI通道下单后 status=SUBMITTED，但实际无法确认是否成交，filled_volume 始终为0 |
| 无成交确认机制 | 下单后没有轮询委托状态的逻辑，依赖定期同步（60秒），存在时间差风险 |
| 错误处理粗糙 | 执行失败时仅返回 REJECTED/ERROR，无重试机制 |
| 期货版过于简化 | 炒单模式假设合约已选中，直接输入手数+点按钮，无合约切换逻辑 |

#### 2.2.3 core/context.py — 策略上下文

**问题等级：中**

| 问题 | 说明 |
|------|------|
| 股票版 vs 期货版不兼容 | 股票版用 `stock_code`/`volume`，期货版用 `contract`/`lots`/`direction`，无法统一 |
| T+1处理不完整 | 通达信版 context.py 注释"简化：全部可卖（T+1暂不考虑）"，但同花顺版 risk_gate 已加T+1检查 |
| 回调注入不一致 | 股票版 `set_callbacks` 参数必填，期货版参数可选（`Callable = None`） |
| 持仓更新直接操作内部属性 | `_update_position`/`_update_account` 直接修改 `_positions`/`_account`，无事件通知 |

#### 2.2.4 core/signal.py — 信号

**问题等级：低**

- 股票版和期货版 Signal 结构不同（stock_code/volume vs contract/lots），合理但需统一抽象
- 期货版增加了 `resolved_action`/`is_open`/`is_long` 等属性，设计较好
- 期货版炒单快捷映射（buy→open_long, sell→close_long）实用

#### 2.2.5 core/risk_gate.py — 风控闸门

**问题等级：中**

| 问题 | 说明 |
|------|------|
| 三版代码几乎相同但独立维护 | DEFAULT_RISK_CONFIG 重复定义三次 |
| 期货版增加了 max_single_lots 但未在基类抽象 | 配置项散落在各版本 |
| 同花顺版增加了 T+1 可卖量检查 | 改进未回推到通达信版 |
| 期货版关卡编号重复 | 关卡4出现两次（日笔数 + 日亏损），注释遗留 |
| 无持仓集中度风控 | 期货版 config 有 max_position_lots 但 risk_gate 未实现 |

#### 2.2.6 core/risk_stats.py — 风控统计

**问题等级：中**

| 问题 | 说明 |
|------|------|
| 连续亏损计数逻辑可疑 | 成功下单时 `consecutive_losses = max(0, consecutive_losses - 1)`，意味着一次成功就能减少连续亏损计数，但亏损记录时 +1，逻辑不对称 |
| 撤单惩罚 | 撤单算作 consecutive_losses +1 但不算 daily_order_count，语义模糊 |
| 无持久化 | 风控统计仅内存维护，进程重启后丢失 |

#### 2.2.7 data/quote_fetcher.py — 行情获取

**问题等级：高**

| 问题 | 说明 |
|------|------|
| 同花顺版性能问题 | `ak.stock_zh_a_spot_em()` 每次调用获取全市场4000+股票数据，仅取1只，极浪费 |
| 无行情缓存（股票版） | 通达信版和同花顺版每次刷新都重新请求，无TTL缓存 |
| 新浪API不稳定 | 期货版依赖新浪HTTP接口，该接口无官方保障，可能随时变更 |
| 无降级重试 | 行情获取失败后无重试机制，直接跳过 |
| 期货版缓存全局变量 | `_quote_cache`/`_cache_ts` 用全局变量，多合约时缓存策略不合理（一个合约更新就刷新全局时间戳） |

#### 2.2.8 ths_config/ — 同花顺适配层

**问题等级：中**

| 问题 | 说明 |
|------|------|
| 跨进程内存读取 | `_get_selected_treeview_text()` 使用 VirtualAllocEx/ReadProcessMemory 读取32位进程内存，实现正确但风险高 |
| 导航不可靠 | 树形菜单导航通过键盘遍历（Home + Down × 50），效率低且可能定位错误 |
| 控件映射硬编码 | `ths_controls.py` 中按钮名称、Edit索引等硬编码，THS版本更新即失效 |
| tabctrl导航未实现 | `_navigate_by_tabctrl()` 标注 TODO，未完成 |

#### 2.2.9 utils_common/human_simulator.py — 模拟真人

**问题等级：低（功能完整但需注意合规）**

- 贝塞尔曲线鼠标轨迹 + 随机抖动 + 速度变化，实现质量高
- 操作录制/回放功能完整
- **合规风险**：模拟真人操作规避自动化检测，可能违反券商服务协议

#### 2.2.10 export_parser.py — 期货导出解析

**问题等级：中**

- 动态列映射（`_build_trade_column_map`）设计好，能适应不同格式
- 但文件编码假设 gbk/utf-8，可能遇到其他编码
- 导出文件时间判断（5分钟内）可能误判旧文件

---

## 三、三版本差异与代码复用分析

### 3.1 代码复用程度：★★☆☆☆（2/5）— 严重不足

| 模块 | 通达信→同花顺复用 | 通达信→期货复用 | 说明 |
|------|-------------------|-----------------|------|
| main.py | ~85%复制 | ~70%复制 | 结构相同，变量名不同 |
| executor.py | ~40%复用 | ~30%复用 | THS去掉API通道，期货简化为炒单 |
| core/context.py | ~60%复制 | ~50%复制 | 字段名不同（stock_code vs contract） |
| core/signal.py | 结构相同 | 结构不同 | 期货版扩展了action体系 |
| core/order.py | 完全复制 | 完全复制 | 三版一致 |
| core/risk_gate.py | ~90%复制 | ~85%复制 | 仅THS增加T+1检查，期货增加手数限制 |
| core/risk_stats.py | 完全复制 | 完全复制 | 三版一致 |
| core/strategy_base.py | 完全复制 | 完全复制 | 三版一致 |
| core/bar.py | 完全复制 | 完全复制 | 三版一致 |
| utils_common/ | ~60%复用 | ~55%复用 | THS版精简了诊断工具，期货版精简了UIA工具 |
| data/quote_fetcher.py | 完全不同 | 完全不同 | 三个不同行情源 |
| executions/ | 各自实现 | 各自实现 | UI操作逻辑不同 |

### 3.2 关键差异总结

| 差异点 | 通达信版 | 同花顺版 | 期货版 |
|--------|---------|---------|--------|
| 执行通道 | API + UI双通道 | 仅UI | 仅UI（炒单模式） |
| 行情源 | TdxQuant本地 | akshare网络 | 新浪HTTP + AKShare |
| 导航方式 | 左侧菜单/快捷键 | SysTreeView32树形菜单 | F1/F2快捷键 |
| 数据读取 | UI控件 + 剪贴板 + 导出 | Static/Edit控件读取 | 导出文件解析 |
| 窗口类型 | 独立交易窗口 | 内嵌交易面板（Afx类名） | 独立交易窗口 |
| 进程位数 | 64位 | 32位（需跨进程内存读取） | 32/64位 |
| T+1处理 | 未实现 | risk_gate已实现 | 不适用（期货T+0） |
| 佣金计算 | 有（万2.5+印花税） | 有（相同逻辑） | 无（由交易所扣） |
| dry-run | 无 | 无 | 有 |
| 飞书通知 | 无 | 无 | v1.01新增feishu_bot |

---

## 四、当前存在的问题和风险

### 4.1 严重问题（P0）

| # | 问题 | 影响 | 涉及版本 |
|---|------|------|---------|
| 1 | **API撤单未实现** | 通达信API通道下单后无法程序撤单，只能手动撤单，实盘风险极高 | 通达信版 |
| 2 | **无成交确认机制** | UI通道下单后 status=SUBMITTED，filled_volume=0，无法确认是否真正成交 | 全部 |
| 3 | **行情性能问题** | 同花顺版每次行情刷新获取全市场数据，延迟高、流量大，可能触发限频 | 同花顺版 |
| 4 | **新浪API无保障** | 期货版依赖非官方HTTP接口，可能随时失效 | 期货版 |
| 5 | **持仓同步时间差** | 股票版60秒同步一次，期货版10秒，期间策略可能基于过期持仓做决策 | 全部 |

### 4.2 高风险问题（P1）

| # | 问题 | 影响 | 涉及版本 |
|---|------|------|---------|
| 6 | **代码三份独立维护** | bug修复需改三处，极易遗漏，已出现（T+1检查仅THS有） | 全部 |
| 7 | **无单元测试** | 重构和修改无保障，回归风险高 | 全部 |
| 8 | **风控统计无持久化** | 进程重启后风控状态丢失，可能绕过日笔数/亏损限制 | 全部 |
| 9 | **THS树形导航不可靠** | 键盘遍历方式可能定位到错误节点 | 同花顺版 |
| 10 | **期货版无合约切换** | 炒单模式假设合约已预选，无法动态切换主力合约 | 期货版 |
| 11 | **配置硬编码** | TDX路径、博易路径、按钮名称等硬编码，换机器即失效 | 全部 |

### 4.3 中等问题（P2）

| # | 问题 | 影响 | 涉及版本 |
|---|------|------|---------|
| 12 | 无优雅退出机制 | 仅 KeyboardInterrupt，无信号处理、无状态保存 | 全部 |
| 13 | 日志格式不统一 | 通达信版用 f-string，同花顺版用 % 格式化 | 通达信/同花顺 |
| 14 | 无行情缓存（股票版） | 每次刷新重新请求，可能触发限频 | 通达信/同花顺 |
| 15 | 期货版风控 max_position_lots 未实现 | 配置存在但代码未检查 | 期货版 |
| 16 | 飞书机器人代码不完整 | v1.01 的 bot.py 有语法错误（`os.env...ET`） | 期货版v1.01 |
| 17 | 无回测框架 | 策略只能实盘/模拟盘验证，无法历史回测 | 全部 |

### 4.4 合规风险

| # | 风险 | 说明 |
|---|------|------|
| 18 | 模拟真人操作 | human_simulator.py 的设计目的是规避自动化检测，可能违反券商服务协议 |
| 19 | UI自动化交易 | 通过操控交易软件UI下单，非官方授权接口，券商可能封禁 |
| 20 | 跨进程内存读取 | THS版读取32位进程内存，可能触发安全软件告警 |

---

## 五、开发建议和改进方向

### 5.1 紧急修复（建议1周内）

1. **实现API撤单**：通达信版 `_cancel_by_api()` 必须补全，否则API通道不可用于实盘
2. **修复行情性能**：同花顺版改用 `ak.stock_individual_info_em` 或缓存全市场数据，避免每次取全量
3. **修复飞书bot语法错误**：v1.01 的 `os.env...ET` 应为 `os.environ.get("FEISHU_APP_SECRET", "")`
4. **增加行情缓存**：股票版增加TTL缓存（参考期货版实现）

### 5.2 架构重构（建议1-2月）

#### 5.2.1 统一核心框架

```
quantumn-core/           # 统一核心包
├── core/
│   ├── signal.py        # 统一Signal（支持股票/期货字段）
│   ├── order.py         # 统一Order/OrderResult
│   ├── context.py       # 抽象Context基类
│   ├── risk_gate.py     # 统一风控（可扩展关卡）
│   ├── risk_stats.py    # 统一风控统计
│   ├── strategy_base.py # 统一策略基类
│   └── bar.py           # 统一K线数据
├── executor/
│   ├── base.py          # 执行器基类
│   ├── api_channel.py   # API通道抽象
│   └── ui_channel.py    # UI通道抽象
├── data/
│   ├── quote_base.py    # 行情源基类
│   └── cache.py         # 统一行情缓存
├── engine.py            # 统一主循环引擎
└── config_base.py       # 配置基类

quantumn-tdx/            # 通达信适配包
├── tdx_executor.py
├── tdx_quote.py
├── tdx_navigator.py
└── tdx_config.py

quantumn-ths/            # 同花顺适配包
├── ths_executor.py
├── ths_quote.py
├── ths_adapter.py       # THSUIAdapter
├── ths_controls.py
└── ths_config.py

quantumn-futures/        # 期货适配包
├── futures_executor.py
├── futures_quote.py
├── export_parser.py
└── futures_config.py
```

#### 5.2.2 关键抽象

1. **行情源抽象**：定义 `QuoteProvider` 接口，各版本实现具体获取逻辑
2. **执行器抽象**：定义 `ExecutionChannel` 接口，API/UI通道统一接口
3. **导航器抽象**：定义 `Navigator` 接口，各客户端实现自己的导航逻辑
4. **数据获取抽象**：定义 `DataFetcher` 接口，统一持仓/账户/成交获取方式

#### 5.2.3 成交确认机制

```
下单 → 轮询委托状态（API查询/UI读取）→ 确认成交 → 更新持仓
```

建议增加 `OrderTracker` 模块，负责：
- 下单后定期查询委托状态
- 超时未成交自动撤单
- 成交后触发持仓更新

### 5.3 功能增强（建议2-3月）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 回测框架 | 基于历史数据回测策略，计算夏普/最大回撤等指标 |
| P0 | 成交确认 | OrderTracker 模块，轮询委托状态 |
| P1 | 风控持久化 | SQLite/JSON 持久化风控统计，重启不丢失 |
| P1 | 优雅退出 | 信号处理 + 状态保存 + 策略清理 |
| P1 | 配置中心 | YAML/TOML 配置文件 + 环境变量覆盖 |
| P2 | 通知系统 | 统一通知接口（飞书/钉钉/邮件），v1.01的飞书bot应抽象为插件 |
| P2 | 日志聚合 | 结构化日志 + ELK/Loki 集成 |
| P2 | 监控面板 | Web UI 实时展示持仓/盈亏/风控状态 |

---

## 六、CiviBBS插件体系适配评估

### 6.1 适配可行性：★★★☆☆（3/5）— 有条件适配

**有利因素：**
- 管道架构天然适合插件化：行情源、策略、风控、执行器均可独立替换
- 策略基类已具备插件接口雏形（initialize/on_bar/on_order_result）
- 风控闸门关卡式设计，可扩展为可插拔的风控规则链

**不利因素：**
- 当前三版代码耦合度高，直接纳入需大量重构
- UI自动化层与具体客户端深度绑定，无法通用化
- 无插件注册/发现机制
- 无事件总线，模块间通信靠直接调用

### 6.2 建议纳入方式

**不建议直接纳入**，建议分两步：

**第一步：提取核心框架为独立包（quantumn-core）**
- 将 Signal/Order/Context/RiskGate/Strategy/Bar 等核心数据结构和接口提取为纯Python包
- 该包无UI依赖、无平台依赖，可作为CiviBBS的基础量化插件

**第二步：各平台适配器作为独立插件**
- `quantumn-tdx`：通达信适配插件
- `quantumn-ths`：同花顺适配插件
- `quantumn-futures`：期货适配插件
- 各插件声明依赖 `quantumn-core`，实现各自的 Executor/QuoteProvider/Navigator

**插件接口设计建议：**

```python
class QuantumnPlugin(CiviBBSPlugin):
    """Quantumn量化交易插件基类"""
    
    name = "quantumn"
    version = "1.0.0"
    
    # 插件生命周期
    def on_load(self, ctx): pass
    def on_unload(self, ctx): pass
    
    # 事件订阅
    def subscribe_events(self):
        return ["quote:update", "signal:generated", "order:filled"]
    
    # 扩展点
    def register_strategies(self): return []
    def register_risk_rules(self): return []
    def register_quote_providers(self): return []
    def register_executors(self): return []
```

### 6.3 纳入路线图

| 阶段 | 时间 | 目标 |
|------|------|------|
| Phase 1 | 1-2周 | 修复P0问题，统一核心数据结构 |
| Phase 2 | 1-2月 | 提取 quantumn-core，实现插件注册机制 |
| Phase 3 | 2-3月 | 各平台适配器插件化，接入CiviBBS事件总线 |
| Phase 4 | 3-4月 | 回测框架、监控面板、通知系统 |

---

## 七、总结

### 7.1 评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ★★★☆☆ | 管道架构思路正确，但实现未做抽象 |
| 代码质量 | ★★☆☆☆ | 大量重复代码，缺少测试和规范 |
| 功能完整度 | ★★★☆☆ | 基本交易流程可用，但成交确认/撤单等关键功能缺失 |
| 风控体系 | ★★★☆☆ | 闸门设计合理，但统计逻辑有瑕疵且无持久化 |
| 可维护性 | ★★☆☆☆ | 三版独立维护，改一处需改三处 |
| 实盘可用性 | ★★☆☆☆ | API撤单未实现、成交无确认，不适合直接实盘 |
| CiviBBS适配 | ★★★☆☆ | 架构有插件化潜力，但需重构 |

### 7.2 核心结论

1. **系统处于"能跑但不能用"阶段**：基本流程通了，但关键环节（成交确认、撤单、行情可靠性）存在硬伤
2. **最大的技术债是代码复制**：三版代码 60-90% 重复，已出现改A忘B的情况（T+1检查）
3. **最大的风险是合规**：UI自动化+模拟真人的交易方式，存在被券商封禁的法律风险
4. **建议先修P0问题再考虑插件化**：在核心功能可靠之前，插件化是过早优化

---

*报告完*
