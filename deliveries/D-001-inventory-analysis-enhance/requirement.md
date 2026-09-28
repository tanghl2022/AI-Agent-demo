# D-001 库存异常原因分析增强

## Status

- AI-SDLC 阶段：DESIGN
- DEFINE 状态：APPROVED
- DEFINE Review：通过
- 当前门禁：等待 G1

## Background

当前仓库已经具备库存异常分析的基础链路：

- 主 Agent 支持 `INVENTORY_ANALYSIS` 意图，并能将分析类请求路由到 `InventoryAnalysisNode`；
- `InventoryAnalysisSubAgent` 支持由 LLM 动态选择只读 Tool、执行多轮 Tool Calling，并在达到最大轮次后停止；
- 当前可用的库存查询 Tool 包括库存汇总、库存组成和库位查询；
- 当前 Prompt 要求不猜测数据、Tool 失败时不伪造结果、证据不足时说明缺少的信息；
- 已接受的架构要求动态分析遵循 `SubAgent -> Tool Calling -> MCP Server -> Java WMS API`，并要求确定性业务规则由 Java WMS Service 负责；
- 仓库内的 Evidence-Driven Analysis 决策进一步明确了“No Evidence, No Deterministic Conclusion”。

但是，当前能力主要能描述物料的总库存、预占库存、冻结库存、可用库存和库位分布。它尚不能稳定回答“为什么异常”：缺少能够证明预占、冻结、状态、订单、任务、批次、出入库、库存流水等原因的查询能力，也缺少统一、可追溯的证据结构和原因表达规则。

因此，需要增强现有库存异常原因分析能力，使其能够在受控的只读边界内收集相关证据、区分事实与推断，并给出可追溯且不过度断言的原因分析。

## Goal

增强 InventoryAnalysisSubAgent 的库存异常原因分析能力，使系统能够：

- 识别用户提出的库存异常及原因分析诉求；
- 根据问题动态选择经授权的只读库存相关 Tool；
- 从 Java WMS API 获取真实、结构化、可追溯的业务证据；
- 区分已证实原因、可能原因、排除项与未知项；
- 将关键结论关联到具体查询证据；
- 在证据不足、冲突、部分失败或完全失败时给出准确的限制说明；
- 始终保持只读，不因分析结论自动执行库存或设备写操作。

本需求不允许 LLM 自行创造原因分类、业务阈值或确定性规则。

## Existing Capability and Gap Analysis

### 已有能力

1. `INVENTORY_ANALYSIS` 已存在于意图模型、识别 Prompt、确定性路由和主 Graph 中。
2. `InventoryAnalysisNode` 已负责调用 `InventoryAnalysisSubAgent`。
3. `InventoryAnalysisSubAgent` 已具备：
   - 动态 Tool Calling；
   - 多轮查询；
   - Tool 名称白名单映射；
   - Tool 不存在和 Tool 异常的降级结果；
   - 最大 8 轮的防无限循环保护。
4. 当前只读 Tool 包括：
   - `query_stock`；
   - `query_inventory_detail`；
   - `query_location`。
5. 当前库存数据包括物料编码、总库存、预占库存、冻结库存和可用库存。
6. 当前库位数据包括物料编码、库位编码和库位数量。
7. WMS Adapter 已通过 Port 调用 Java WMS 库存与库位查询 API，并将外部异常映射为业务层错误。
8. 当前 Prompt 已包含不猜测、按需调用 Tool、失败不伪造、证据不足时说明缺口等基本约束。
9. 已有 Architecture Test 检查应用层与 Integration 层的依赖边界。

### 主要差距

1. **原因证据范围不足**：当前 Tool 只能获得库存数量组成和库位分布，不能查询预占来源、冻结记录及原因、库存状态、批次属性、订单、作业任务、出入库记录、库存流水或其他可能的原因证据。
2. **异常与原因分类未定义**：仓库中没有经业务确认的库存异常类型、原因分类、判定条件、排除条件或优先级规则。
3. **因果结论边界不明确**：当前 Prompt 要求输出“最可能的异常原因”，但没有定义何种证据足以确认原因、何时只能描述相关现象或候选原因。
4. **缺少统一 Evidence 模型**：当前 Tool 直接返回 dataclass 转换结果或普通字典，没有统一的 `tool`、`status`、`source`、`query`、`data/error`、`evidence_id`、`timestamp` 等证据字段。
5. **结论不可结构化追溯**：SubAgent 最终只返回字符串，当前没有结论与 Evidence ID 的结构化关联，也没有事实、推断、未知信息的明确分类。
6. **MCP 能力尚未形成真实链路**：MCP Server 仅有返回固定模拟数据的 `get_stock`；`wms_mcp/tools/inventory.py` 与 `wms_mcp/clients/wms_client.py` 为空，没有真实 inventory detail、location 或原因调查 Tool。
7. **实际调用链与正式架构存在差距**：当前 SubAgent 绑定进程内 Capability Tool，未通过 MCP Client、MCP Server 调用 Java WMS API。
8. **主图问题传递存在缺口**：`InventoryAnalysisNode` 从 state 读取 `question`，但 `AgentState`、意图识别和仓库内其他代码使用 `user_message`，未发现 `question` 的赋值路径；主图中的 SubAgent 可能收到空问题。
9. **分析参数校验不足**：`INVENTORY_ANALYSIS` 当前无条件通过参数校验；物料、仓库、批次、订单或其他调查范围中哪些是必填项尚未定义。
10. **错误语义不完整**：当前 Tool 失败结果只有 `success` 和字符串 `error`，不能稳定区分无数据、无权限、参数错误、超时、部分失败和上游不可用。
11. **部分成功与证据冲突未定义**：多个 Tool 返回不一致时间点、相互冲突数据或部分失败时，当前没有明确行为规则。
12. **可观测性未贯通分析证据**：存在独立的 Tool 耗时跟踪器，但当前 SubAgent Tool 循环未展示 Evidence ID、数据源、请求上下文、时间戳与结论的完整关联。
13. **自动化测试不足**：没有 InventoryAnalysisSubAgent 自动化行为测试、库存异常原因场景测试、分析节点输入传递测试、库存分析 MCP Contract Test、Intent Evaluation 或 Agent Evaluation。
14. **现有 MCP 测试覆盖有限**：只验证 `get_stock` 返回非空结构，不验证真实 WMS 调用、字段语义、错误映射、权限隔离或证据结构。
15. **规范文件为空**：`specs/inventory-analysis/behaviors.md` 和 `specs/inventory-query/behaviors.md` 当前为空，不能提供已确认的原因分析规则。
16. **边界文档为空**：`architecture/boundaries.md` 当前为空，本需求只能遵循 `AGENTS.md`、`architecture.md` 和已接受 ADR 已明确的边界。

## Scope

本需求范围包括：

- 增强库存异常原因分析请求的识别与上下文传递；
- 定义库存异常原因分析所需的最小调查范围与补问行为；
- 在已确认的异常类型范围内，通过授权的只读 Tool 收集原因证据；
- 将库存相关查询能力通过符合架构边界的 MCP inventory tools 暴露给 InventoryAnalysisSubAgent；
- 对 Tool 结果采用统一、可追溯的 Evidence 表达；
- 由 InventoryAnalysisSubAgent 综合多项证据，区分事实、确定性结论、可能原因和未知项；
- 对无数据、证据不足、证据冲突、部分失败、无权限、超时和上游错误给出明确反馈；
- 在输出中说明调查对象、调查范围、关键证据、结论限制和后续需要的信息；
- 为后续阶段定义 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation Cases 和 Architecture Rule 验证要求。

具体支持的异常类型、原因目录、证据来源、输入输出契约和诊断规则，必须在 Open Questions 得到确认后才能进入 DESIGN。

## Out of Scope

- 自动冻结、解冻、扣减、调整、移库或处置库存；
- 自动创建、修改或取消入库单、出库单、订单或仓库任务；
- 自动控制堆垛机、输送线、机器人、PLC 或其他设备；
- 由 LLM、SubAgent、Capability 或 MCP Server实现确定性的库存计算、状态机、权限判断或核心业务规则；
- Agent 或 MCP Server 直接访问数据库；
- 未经业务确认扩展到需求预测、补货优化、库存预测、积压分析或其他独立分析领域；
- 保证在证据不足时一定找到根因；
- 本 DEFINE 阶段内修改 Prompt、Graph、Node、Tool、MCP、Java API、业务代码或测试代码；
- 本阶段进入 DESIGN、G1、IMPLEMENT、VERIFY 或 G2。

## Business Rules

以下规则可以从当前需求和已接受架构中确定：

1. 库存异常原因分析属于只读分析能力，不得直接或间接触发任何库存、订单、任务或设备写操作。
2. 重要结论必须由真实 Tool Evidence 支持；没有证据时不得输出确定性原因。
3. 库存数量、状态、业务关系和确定性判定必须来自 Java WMS Service；LLM 不得自行计算、补全或改变确定性业务事实。
4. InventoryAnalysisSubAgent 负责理解问题、动态选择只读 Tool、综合证据和解释结果，不负责核心业务规则、事务、状态机或最终权限判断。
5. MCP Server 负责 Tool 契约、基础参数校验、协议适配、错误映射和可观测性，不得直接访问数据库或复制 Java WMS 核心规则。
6. 分析输出必须区分 Tool 返回的事实、由确定性业务规则给出的结论、基于证据的推断以及未知信息。
7. 仅存在相关现象但缺少充分因果证据时，不得将其表述为已确认根因；最多按业务批准的术语表述为候选或可能原因。
8. 查询失败只表示当前未成功取得数据，不得解释为业务数据不存在、异常不存在或原因已排除。
9. 证据之间冲突时，系统必须披露冲突，不得静默选择对结论最有利的一项证据。
10. 分析必须明确调查对象、查询范围和数据时间点，不得将局部或过期数据外推为全局或当前事实。
11. 查询必须遵守用户、租户、仓库和数据权限隔离；最终权限由 Java WMS API 判定。
12. Tool 只能从显式授权的只读集合中选择；未知 Tool 或写 Tool 不得执行。
13. 达到最大 Tool Calling 轮次仍无法取得充分证据时，必须终止并说明证据缺口，不得继续无限调用或编造结论。
14. 如果分析结果提出后续操作，只能作为未执行的建议；实际高风险写操作必须另行进入 Proposal、Workflow、Human Approval、受控 MCP Tool 和 Java WMS API 流程。

## Open Questions

以下问题无法从当前代码、架构文档或需求中确定，必须在 DESIGN/G1 前由业务与架构相关方确认：

> DEFINE Review 处置：Review 已确认以下剩余问题均属于技术设计问题，不阻塞需求确认。DEFINE 已 APPROVED；这些问题由 `decisions.md`、`contracts.md` 和 `tasks.md` 进行技术收敛，并在 G1 审核，不再作为 DEFINE 阻塞项。

1. 本需求要支持哪些“库存异常”类型，例如可用量不足、预占异常、冻结异常、账面组成异常、库位分布异常、批次/状态异常或其他类型？
2. 每种异常允许输出哪些原因分类？是否存在统一的原因编码、名称、层级和业务定义？
3. 哪些原因可以由 Java WMS Service 确定性判定，哪些只允许由 Agent 作为候选原因解释？
4. 什么证据组合足以确认某个原因？确认、可能、无法判断、已排除等状态如何定义？
5. 是否需要原因置信度或评分？如需要，由谁计算、采用何种范围和阈值、是否允许 LLM 生成？
6. 每类异常需要查询哪些数据源：预占记录、冻结记录、订单、波次、任务、批次、库存状态、质量状态、入库/出库记录、库存流水、库位状态或其他系统？
7. 当前 Java WMS 是否已有上述查询 API？其契约、权限要求、时间范围、分页限制和数据新鲜度是什么？
8. 物料编码是否为原因分析的必填参数？仓库、货主/租户、批次、库位、订单号、任务号、时间范围中哪些必须由用户提供，哪些可以从会话上下文确定？
9. 是否允许分析整个仓库、多物料或多异常对象？若允许，最大范围、分页、Top N 和排序规则是什么？
10. 原因分析的默认时间范围是什么？使用业务时间还是自然时间，采用哪个时区和截止时间？
11. 多个原因同时成立时，应全部展示、按优先级排序，还是只展示主因？优先级由谁定义？
12. 证据互相冲突、来源时间不同或数据版本不一致时，哪一来源具有权威性？
13. 部分 Tool 成功、部分 Tool 失败时，是否允许返回部分分析？如果允许，最低证据要求是什么？
14. 无查询结果与查询失败应分别使用什么标准错误码和用户提示？
15. Evidence 的统一字段、生命周期、存储方式、脱敏要求和审计保留期是什么？
16. 最终响应需要纯文本、结构化原因列表、Evidence 引用，还是同时提供机器可读与用户可读格式？
17. 用户是否需要查看每次 Tool 调用、查询参数、数据源、时间戳和 Evidence ID？哪些信息需要脱敏？
18. 是否复用现有 `INVENTORY_ANALYSIS` 意图，还是为特定异常类型建立子意图或参数模型？
19. 原因分析应复用现有 InventoryAnalysisSubAgent，还是在现有 SubAgent 内划分独立 Capability/策略？该问题需在不违反 SubAgent 准入规则的前提下于 DESIGN 决定。
20. 当前最大 8 轮 Tool Calling 是否适合原因分析？单次分析的超时、重试、并发和调用成本上限是多少？
21. 当用户只说“库存异常”而没有明确现象时，系统应先查询基础库存、先追问异常表现，还是执行其他流程？
22. 是否允许 Agent 基于数量关系提出候选解释，例如“预占数量较高可能导致可用量低”？允许使用哪些措辞和限制条件？
23. 是否需要给出处置建议？如果需要，允许建议的类型、风险提示和审批入口是什么？
24. 主图中 `question` 与 `user_message` 的规范字段应如何统一，并如何保证多轮上下文传递？
25. 正式实现是否需要一次性将现有进程内 Tool 全部迁移到 MCP，还是允许分阶段过渡？过渡期调用链和验收边界需在 DESIGN 明确。

## Acceptance Criteria

以下条件描述目标行为，不替代 Open Questions 中待确认的异常目录、原因规则和 Tool 契约：

1. 用户提出需要解释库存异常、原因或综合判断的问题时，系统能够识别为库存分析请求；明确的单一库存或库位查询仍走确定性查询能力。
2. InventoryAnalysisNode 将用户实际提出的分析问题完整传递给 InventoryAnalysisSubAgent，不得以空问题启动分析。
3. 请求缺少经确认的必填调查范围时，系统明确补问缺失参数，不提前生成原因结论。
4. 参数完整且用户有权限时，InventoryAnalysisSubAgent 只能通过经授权的只读 MCP Tool 查询 Java WMS API 所提供的业务证据。
5. 每项重要事实和确定性原因结论能够追溯到一个或多个 Tool Evidence，并包含足以识别数据来源和时间点的信息。
6. 回答明确区分事实、确定性结论、候选原因、已排除项和未知项，不把相关性描述为已证明的因果关系。
7. 当证据足以满足经批准的原因规则时，系统按该规则返回原因，并说明关键证据。
8. 当证据不足时，系统明确返回无法确认原因及缺失信息，不猜测确定性根因。
9. 当证据冲突时，系统明确披露冲突及受影响的结论，不静默忽略冲突证据。
10. 当部分 Tool 失败时，系统按经确认的部分成功规则处理，并明确标识未完成的调查范围。
11. 当全部必要 Tool 失败、超时或返回非法响应时，系统明确说明分析失败，不将失败解释为无异常或无原因。
12. 无权限、租户不匹配或仓库无权访问时，系统不泄露受限库存数据，并保留 Java WMS API 的最终权限判定。
13. 达到 Tool Calling 轮次或资源上限仍无法完成分析时，系统停止调用并说明当前证据与缺口。
14. 整个原因分析过程不调用写 Tool，不修改库存、订单、任务或设备状态。
15. 如回答包含处置建议，必须明确其为未执行建议；任何实际写操作必须进入独立审批流程。
16. 后续实现具备并通过与变更范围匹配的 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation Cases 和 Architecture Rule 检查。
17. Open Questions 中影响异常范围、原因目录、证据充分性、输入输出契约和错误语义的问题在 G1 前形成明确决议；未决时不得进入 IMPLEMENT。

