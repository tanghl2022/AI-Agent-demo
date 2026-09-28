# D-001 库存异常原因分析增强 Architecture Decisions

## Status

- 阶段：DESIGN
- DEFINE：APPROVED
- DESIGN：COMPLETE
- Gate：等待 G1
- Implementation：NOT STARTED

## Design Baseline

本设计只实现 `AVAILABLE_STOCK_LOW`，只调查 `RESERVED_STOCK_HIGH`、`FROZEN_STOCK_HIGH`，只使用 `InventorySummaryEvidence`、`ReservationEvidence`、`FreezeEvidence`。任何其他异常、原因或 Evidence 类型均为 Scope Change。

## D1 整体执行流程

`AVAILABLE_STOCK_LOW` 使用以下流程：

```text
User Request
→ Main Agent / Intent Recognition
→ Context Merge
→ Parameter & Trusted Context Validation
→ InventoryAnalysisNode
→ InventoryAnalysisSubAgent
→ Authorized READ Tool Calling
→ MCP Client
→ MCP Server
→ Java WMS API
→ Evidence Collection
→ Deterministic Result Assembler
→ Natural-language Renderer
→ Structured Result + Answer
```

Main Graph 只负责路由和状态；SubAgent 只负责分析计划及只读 Tool 选择；Java WMS 负责库存事实、确定性规则、权限和隔离；结果组装器负责按已批准分类机械映射，不计算库存业务规则。

## D2 复用现有 Intent、Node 与 SubAgent

复用 `INVENTORY_ANALYSIS`、`InventoryAnalysisNode`、`InventoryAnalysisSubAgent`，不新增 Intent、SubAgent 或固定 Workflow。

原因分析存在动态 Tool 选择与多轮证据收集，符合 ADR-002。明确单一库存查询继续通过 Node → Capability，不强制 MCP 化。

## D3 InventoryAnalysisSubAgent 职责边界

SubAgent 负责：

- 理解用户的 `AVAILABLE_STOCK_LOW` 分析目标；
- 在三个显式授权 READ Tool 中选择调用顺序；
- 根据已收集 Evidence 决定是否继续查询；
- 将 Evidence 交给确定性结果组装器；
- 在最大轮次或总时限到达时停止。

SubAgent 不负责：

- 计算库存数量；
- 定义“高”的阈值；
- 判定 Java WMS 权限；
- 生成新的原因编码；
- 生成数值置信度；
- 将 `POSSIBLE_CAUSE` 升级为已确认根因；
- 调用任何写 Tool。

## D4 Java WMS Service 边界

Java WMS 是以下内容的唯一权威来源：

- 总库存、可用库存、预占库存、冻结库存；
- `AVAILABLE_STOCK_LOW`、`RESERVED_STOCK_HIGH`、`FROZEN_STOCK_HIGH` 的确定性规则结果与规则版本；
- 预占、冻结业务事实；
- user、tenant、warehouse 权限和数据隔离；
- 数据一致性及查询时点。

Prompt、Python Service、MCP Server 均不得复制或替代这些规则。Java WMS 没有确定性规则结果时，系统只能输出 `POSSIBLE_CAUSE` 或 `UNKNOWN`。

## D5 MCP Server 边界

MCP Server 负责：

- 暴露三个 V1 READ Tool；
- 校验 Tool 基础输入；
- 将受信任调用上下文转发给 Java WMS；
- 调用 Java WMS API；
- 映射错误并包装 Evidence Contract；
- 生成 `evidenceId`；
- 记录 Tool、时延、状态和 Trace 元数据。

MCP Server 不负责业务阈值、原因计算、权限最终判定、数据库访问或写操作。MCP Server 包中不得出现数据库 Driver 或 Repository。

## D6 Evidence 职责与关系

### InventorySummaryEvidence

提供分析锚点：物料、数量构成、Java WMS 对 `AVAILABLE_STOCK_LOW` 的确定性 assessment、数据版本和查询时点。

### ReservationEvidence

提供预占事实及 Java WMS 对 `RESERVED_STOCK_HIGH` 的 assessment，不负责冻结解释。

### FreezeEvidence

提供冻结事实及 Java WMS 对 `FROZEN_STOCK_HIGH` 的 assessment，不负责预占解释。

三类 Evidence 彼此独立、通过同一个 `analysisId` 聚合。Summary 是异常上下文，Reservation 和 Freeze 是两个并列调查维度；任一维度失败不得污染另一维度的事实。

## D7 三个只读 MCP Tool

V1 Tool 白名单固定为：

- `get_inventory_summary_evidence`
- `get_reservation_evidence`
- `get_freeze_evidence`

LLM 可见输入只有 `material_code`。tenant、warehouse、user、requestId、analysisId 和认证信息由 MCP Client 从受信任上下文附加，不进入模型可填写的 Tool schema。

应用启动时必须校验 Tool 集合与白名单完全一致；发现写 Tool、未知 Tool 或缺少 Tool 时 fail closed。

## D8 FACT / POSSIBLE_CAUSE / UNKNOWN 产生规则

结果由确定性 `InventoryAnalysisResultAssembler` 产生：

- `FACT`：Evidence 中 Java WMS 返回的原始事实，或 Java WMS 明确返回的确定性 assessment；
- `POSSIBLE_CAUSE`：对应 Reservation/Freeze assessment 表明候选条件相关，但 Java WMS 未确认因果关系；只能使用两个批准的原因编码；
- `UNKNOWN`：Evidence 缺失、失败、无数据、assessment 为未知、证据冲突或因时间版本不一致无法判断。

LLM 不直接写入分类集合。Prompt 只指导 Tool 选择与停止条件，不包含阈值和业务计算。

## D9 Analysis Status 与 PARTIAL

状态只允许：

- `SUCCESS`：三个 Evidence 维度均完成；`NO_DATA` 也视为完成，但必须产生相应 `UNKNOWN` 或事实说明；
- `PARTIAL`：至少一个维度成功完成，至少一个维度失败、超时或不可用；
- `FAILED`：没有任何可用 Evidence，或权限失败，或可信上下文缺失且无法继续。

`PARTIAL` 必须列出 `successfulScopes`、`failedScopes`、`limitations`。失败维度不得用于确认或排除原因。任何 `FORBIDDEN` 结果整体 fail closed，不返回已收集的受限业务数据。

## D10 Evidence Conflict

冲突检测由确定性组装器完成，不交给 LLM：

- 同一业务字段、同一 `inventoryVersion` 值不一致，标记为 `VALUE_CONFLICT`；
- 不同 `inventoryVersion` 或查询时点造成不一致，标记为 `TEMPORAL_CONFLICT`；
- 冲突 Evidence 原样保留并互相引用；
- 受影响的结论进入 `UNKNOWN`；
- 分析状态至少为 `PARTIAL`，并在 `limitations` 披露冲突；
- 不设置静默数据源优先级，不由 LLM 选择“更可信”的值。

## D11 统一 question / user_message

`AgentState.user_message` 是本轮原始问题的唯一字段。删除分析链路对 `question` 的读取，不向 State 新增同义字段。

`InventoryAnalysisNode` 使用 `user_message`、`material_code`、`request_context` 构造 `InventoryAnalysisRequest`，调用 `InventoryAnalysisSubAgent.ainvoke(request)`。

历史参数仍由现有 Context Merge Node 处理；原始历史消息不得替代本轮 `user_message`。

## D12 Request / Session Context

新增受信任 `RequestContext`：

- `requestId`
- `conversationId`
- `userId`
- `tenantId`
- `warehouseId`
- `authorization`

API 层通过认证/Session dependency 建立该上下文，AgentService 将其写入 State，Node 只读取不修改，MCP Client 将其作为传输元数据转发。`authorization` 不进入 Checkpoint、Prompt、ToolMessage、日志或结构化结果。

user/tenant 缺失时要求重新认证或选择受信任 Session，不接受自然语言声明替代身份。warehouse 缺失时可以补问仓库，再由 Java WMS 校验用户是否有权访问。

## D13 最大轮次、Timeout、Retry 与降级

- Tool Calling 最大轮次：保留现有 8 轮；
- 同一 Evidence Tool + materialCode + context 在一次 analysis 中最多真实调用一次，重复调用返回缓存 Evidence；
- 单次 MCP Tool timeout：10 秒，可配置；
- 单次分析总 deadline：30 秒，可配置；
- 仅对连接失败、timeout、HTTP 502/503/504 重试 1 次；
- 重试退避：200ms，受总 deadline 约束；
- 400/401/403/404/409/422 和 schema 错误不重试；
- 连续 5 次可重试失败后熔断 30 秒，参数可配置；
- 达到轮次、deadline 或熔断时生成失败 Evidence，按 PARTIAL/FAILED 规则降级。

所有重试复用 requestId、analysisId 和 toolCallId，不生成重复 Evidence。

## D14 结构化结果与自然语言回答

`InventoryAnalysisResult` 是唯一事实来源。`InventoryAnalysisAnswerRenderer` 从结构化结果确定性生成自然语言回答，LLM 不再独立生成第二套结论。

自然语言固定包含：调查对象、事实、可能原因、未知项、限制；无建议时不显示建议段。结构化结果与 answer 同时返回，旧客户端仍可只消费 `answer`。

## D15 可观测性、审计与 Evidence Trace

每次分析生成 `analysisId`；每次 Tool Call 生成 `toolCallId`；每个 Tool 结果生成 `evidenceId`。Trace 关系为：

```text
requestId → analysisId → toolCallId → evidenceId → fact/possibleCause/unknown
```

记录事件：analysis start/end、tool start/end、retry、circuit open、evidence collected、conflict detected、result assembled。记录 duration、status、errorCode、Evidence 类型和引用，不记录 authorization、完整 Prompt、未脱敏业务引用或敏感个人信息。

V1 使用 Observability Port 输出结构化日志/Trace，不新增 Agent 直连审计数据库。Evidence Trace 必须能从结果引用回对应 Tool 调用和 Java WMS requestId。

## D16 Capability 与 MCP 的共存

现有 Stock/Location Capability 继续服务固定查询 Node。InventoryAnalysisSubAgent 不再使用 `create_wms_tools` 生成的进程内 Capability Tool，而使用 MCP Client Adapter 提供的三个只读 Tool。

这符合 ADR-001：Capability 仍是稳定内部能力；也符合 ADR-003：动态 Agent Tool Calling 通过 MCP。

## D17 测试与 Evaluation 策略

- Evidence Model、Result Assembler、Renderer、State/Context：Unit Test；
- Java WMS Adapter 与真实 MCP Client：Integration Test；
- 三个 MCP Tool 的 schema、映射、权限上下文和错误：MCP Contract Test；
- `AVAILABLE_STOCK_LOW` 与普通查询/范围外异常：Intent Evaluation；
- FACT/POSSIBLE_CAUSE/UNKNOWN、PARTIAL、冲突、超时：Agent Evaluation；
- 无 Evidence 确认根因、LLM 数值置信度、写 Tool、权限泄漏：Critical Evaluation；
- Ports & Adapters、MCP 无数据库依赖、Tool 白名单：Architecture Test。

## Architecture Compatibility

未发现 requirement/behaviors 与现有架构无法解决的冲突。本设计状态不是 `BLOCKED`。

## G1 Decision

在三个 Artifact 完成一致性检查后，本设计可提交 G1；G1 前不得实施任何 Task。

