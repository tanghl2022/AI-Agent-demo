# D-001 库存积压分析

## Status

- AI-SDLC 阶段：DEFINE
- 状态：待业务确认
- 本阶段不包含设计与实现

## Background

当前仓库已具备基础库存查询、库位查询和库存异常分析能力：

- `QUERY_STOCK` 可查询物料的总库存、预占库存、冻结库存和可用库存；
- `QUERY_LOCATION` 可查询物料的库位分布；
- `InventoryAnalysisSubAgent` 可按问题动态调用只读库存查询工具，并根据真实查询结果解释库存异常；
- 已接受的架构要求 Agentic 查询遵循 `SubAgent -> Tool Calling -> MCP Server -> Java WMS API`，确定性业务规则由 Java WMS Service 负责。

当前能力只能描述“现在有多少库存、库存由什么组成、存放在哪里”，不能基于可验证的时间、流动和价值证据识别库存积压，也不能回答库存积压的范围、依据和原因。

仓库中已有 `D-001-inventory-risk` 定义了基于可用库存占比的库存风险等级。该能力关注可用量不足风险，与本需求关注的库存长期未流动或周转缓慢不是同一业务概念，不应复用可用库存占比作为积压判定规则。

## Goal

增加只读的库存积压分析能力，使用户能够请求分析指定业务范围内的积压库存，并获得：

- 由 WMS 确定性业务能力给出的积压判定结果；
- 支撑结论的结构化事实与统计口径；
- InventoryAnalysisSubAgent 基于真实 Tool 结果生成的解释；
- 在证据不足、查询失败或无权限时，不猜测、不伪造的明确反馈。

本需求不授权 Agent 自行定义积压规则，也不授权 Agent 执行任何库存写操作。

## Existing Capability and Gap Analysis

### 已有能力

1. 主 Agent 已存在 `INVENTORY_ANALYSIS` 意图、确定性路由和 `InventoryAnalysisNode`。
2. `InventoryAnalysisSubAgent` 支持多轮 Tool Calling、最大轮次限制、Tool 异常隔离，并被限制为只读分析。
3. 当前只读 Tool 包括：
   - `query_stock`
   - `query_inventory_detail`
   - `query_location`
4. 当前库存模型包含：
   - `materialCode`
   - `totalQty`
   - `reservedQty`
   - `frozenQty`
   - `availableQty`
5. 当前库位模型包含库位编码和数量。
6. WMS HTTP Adapter 已通过 Port 接入 Java WMS 库存查询 API。

### 主要差距

1. **判定数据不足**：现有模型和 Tool 没有库龄、最后入库时间、最后出库时间、最后移动时间、统计期间出库/消耗量、周转率、库存价值等积压分析证据。
2. **确定性规则缺失**：仓库中没有已确认的积压定义、时间窗口、阈值、分级、例外或计算规则。
3. **分析粒度未定义**：尚未确定按物料、批次、库位、库存明细、仓库或其他维度进行判定。
4. **业务范围未定义**：尚未确定仓库、租户、物料类别、库存状态及时间范围如何限定。
5. **Java WMS 能力缺失或未接入**：当前代码中未发现提供积压分析事实或判定结果的 Java WMS API 契约与 Adapter。
6. **MCP 能力不完整**：当前 MCP Server 只有返回模拟数据的 `get_stock`；`wms_mcp/tools/inventory.py` 和 `wms_mcp/clients/wms_client.py` 为空，没有积压分析 Tool，也没有对应错误映射和业务响应契约。
7. **实际调用链与目标架构存在差距**：当前 `InventoryAnalysisSubAgent` 绑定进程内 Capability Tool，尚未通过 MCP Client 调用 MCP Server。后续 DESIGN 必须在遵守 ADR 的前提下确定迁移或适配方案。
8. **Prompt 范围不足**：当前 Prompt 仅声明可调查库存组成、可用量、预占、冻结和库位，没有积压证据及其解释约束。
9. **参数校验不足**：`INVENTORY_ANALYSIS` 当前无条件通过参数校验；积压分析所需的最小查询范围尚未定义。
10. **测试保障不足**：当前没有自动化的 InventoryAnalysisSubAgent 行为测试、积压意图 Evaluation、积压 Agent Evaluation 或积压 MCP Contract Test；现有 MCP 测试仅验证 Tool 有结构化返回，不验证真实 WMS 调用或字段语义。
11. **已有规范占位**：`specs/inventory-query/behaviors.md` 与 `specs/inventory-analysis/behaviors.md` 当前为空，不能作为积压规则来源。
12. **边界文档占位**：`architecture/boundaries.md` 当前为空；本需求只能遵循 `AGENTS.md`、`architecture.md` 和已接受 ADR 中已经明确的边界。

## Scope

本需求范围包括：

- 识别用户的库存积压分析诉求，并进入库存分析能力；
- 在经确认的租户、仓库、物料及时间等业务范围内查询积压分析事实；
- 由 Java WMS Service 按已批准的确定性业务规则计算或判定积压结果；
- 通过只读 MCP inventory tool 向 InventoryAnalysisSubAgent 提供结构化分析结果与证据；
- 由 InventoryAnalysisSubAgent 解释积压结论、关键证据、数据范围和限制；
- 对参数不足、无匹配库存、证据不足、无权限、Tool 或上游服务失败给出明确反馈；
- 为后续阶段定义所需的 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation 和 Critical Evaluation 场景。

具体输入字段、输出字段、统计口径和判定阈值必须在 Open Questions 得到业务确认后，才能在 DESIGN 阶段固化。

## Out of Scope

- 自动补货、自动采购、自动促销、自动调拨或自动处置积压库存；
- 库存冻结、解冻、调整、扣减、移库、出入库确认或设备控制；
- 由 LLM、Agent、Python Capability 或 MCP Server 自行计算或改变确定性积压规则；
- Agent 或 MCP Server 直接访问数据库；
- 需求预测、销量预测、补货优化或库存优化模型；
- 修改现有库存风险等级规则；
- 本 DEFINE 阶段内的 API、MCP Tool、Agent、Prompt、业务代码或测试代码实现；
- 在本阶段进入 DESIGN、G1、IMPLEMENT、VERIFY 或 G2。

## Business Rules

以下规则可由现有需求和架构确定：

1. 库存积压分析是只读能力，不得直接或间接触发库存写操作。
2. 积压判定属于确定性业务规则，必须由 Java WMS Service 负责；LLM、SubAgent、Capability 和 MCP Server 不得自行计算或猜测判定结果。
3. MCP Server 只负责 Tool 定义、基础参数校验、协议适配、错误映射和可观测性，不得直连数据库或复制 Java WMS 的核心业务规则。
4. InventoryAnalysisSubAgent 只负责理解分析目标、选择已授权的只读 Tool、综合真实结果并解释结论。
5. 所有数量、日期、周转、价值、分类和判定结论必须来自受控 Tool 返回的事实，不得由 Agent 虚构。
6. Tool 结果不足以支持结论时，Agent 必须说明无法判定及缺少的证据，不得给出确定的积压结论。
7. Tool 调用失败或上游返回格式异常时，Agent 必须明确报告失败，不得将失败解释为“无积压库存”。
8. 查询必须遵守用户、租户、仓库隔离和最终权限校验；最终授权由 Java WMS API 判定。
9. Agent 的解释必须能够关联 Tool 返回的关键证据，并说明分析所覆盖的业务范围和统计口径。
10. 如分析产生处置建议，只能作为建议展示；任何后续高风险写操作必须另行进入 Proposal、Workflow、Human Approval、受控 MCP Tool 和 Java WMS API 流程。
11. “可用库存风险”与“库存积压”是不同概念；除非业务另行确认，不得使用现有 `availableRate` 风险等级替代积压判定。

## Open Questions

以下问题无法从当前需求、代码或架构文档中确定，属于进入 DESIGN/G1 前必须确认的业务问题：

1. 业务上如何定义“积压库存”？依据库存年龄、最后一次出库/消耗时间、期间周转率、期间需求量，还是多个指标的组合？
2. 积压判定使用哪个时间起点：首次入库、最近入库、生产日期、收货日期、上架日期、最后移动日期、最后出库日期或其他日期？
3. 判定时间窗口和阈值是多少？是否需要按物料类别、ABC 分类、货主、仓库或业务场景配置不同阈值？
4. 是否需要积压等级；如需要，等级名称、边界和边界值归属如何定义？
5. 判定粒度是什么：物料汇总、仓库+物料、批次、库位库存、容器/LPN、库存明细或其他粒度？不同批次能否相互抵消？
6. 默认查询范围是什么？用户至少需要提供哪些参数；物料编码、仓库、货主/租户和时间范围中哪些是必填项？
7. 是否允许查询整个仓库或多物料的积压清单？若允许，最大范围、分页、排序和 Top N 规则是什么？
8. 哪些库存状态需要排除或单独展示，例如冻结、质检、待处理、不合格、在途、预占、退货或不可销售库存？
9. 零库存、负库存、刚入库库存、无历史流水库存和缺失日期库存如何处理？是“不积压”“无法判定”还是单独状态？
10. 是否需要计算积压数量和积压金额？如需金额，使用哪种成本口径、币种和汇率日期？
11. 是否需要解释积压原因；若需要，哪些原因可以由确定性事实支持，哪些只能标记为可能原因？
12. 分析结果至少需要返回哪些证据字段、统计口径、数据时间点和数据新鲜度信息？
13. “无积压结果”表示当前筛选范围确实没有积压，还是也可能表示数据不足？两者需要怎样区分？
14. 是否需要趋势对比，例如与上一周期相比的积压数量/金额变化？
15. 是否存在业务日历、自然日/工作日、时区或截止时间规则？
16. Java WMS 当前是否已有可复用的库存年龄、库存流水、周转或积压分析 API？若有，其契约、权限和数据延迟是什么？
17. 积压分析应复用通用 `INVENTORY_ANALYSIS` 意图，还是需要独立意图？该选择需结合参数模型、Evaluation 和未来扩展性在 DESIGN 阶段决定。
18. 对 Tool 超时、部分数据成功、跨服务数据时间点不一致的结果，业务允许返回部分分析还是必须整体失败？
19. 是否需要导出、下载、定时报表或主动告警？当前需求只描述交互式分析，其他交付形态尚未确认。

## Acceptance Criteria

以下验收条件描述目标行为，不替代 Open Questions 中待确认的业务口径：

1. 用户提出明确的库存积压分析请求时，系统能够识别为库存分析类请求，而不是普通库存数量查询或写操作请求。
2. 当请求缺少已确认的必填业务范围时，系统明确询问缺失参数，不调用积压分析业务能力。
3. 当参数完整且用户有权限时，InventoryAnalysisSubAgent 通过已授权的只读 MCP inventory tool 获取由 Java WMS Service 生成的积压判定与证据。
4. Agent 展示的积压状态、数量、时间、指标和等级与 Tool 返回一致，不在 LLM 中重新计算确定性结果。
5. 分析结果明确说明查询范围、统计口径、关键证据、数据时间点以及能够确认的结论。
6. 在已确认范围内没有积压库存时，系统明确表述“该范围内无积压结果”，且不将其扩大解释为其他仓库、物料或时间范围均无积压。
7. 证据字段缺失或不足时，系统返回“无法判定”及所缺证据，不猜测积压状态或原因。
8. Tool、MCP 或 Java WMS API 失败时，系统返回可理解的失败信息，不将失败伪装为正常业务结果。
9. 无权限、租户不匹配或仓库无权访问时，不泄露库存数据，并保留 Java WMS API 的最终权限判定。
10. 整个积压分析流程不调用任何写 Tool，不修改库存、订单、任务或设备状态。
11. 如回答包含处置建议，必须明确其为建议且未执行；任何实际写操作必须进入独立的审批工作流。
12. 后续实现必须具备并通过与变更范围相匹配的 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation Cases 和 Architecture Rule 检查。
13. Open Questions 中影响积压定义、输入输出契约和验收预期的问题在 G1 前形成明确决议；未决时不得进入 IMPLEMENT。

