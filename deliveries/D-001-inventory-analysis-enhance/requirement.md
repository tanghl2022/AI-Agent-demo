# D-001 库存异常原因分析增强

## Status

- AI-SDLC 阶段：DEFINE
- DEFINE 状态：APPROVED
- DEFINE Resolution：完成
- DESIGN 状态：PAUSED
- 下一步：重新进入 DESIGN 前等待用户指令

## Background

当前仓库已经具备库存异常分析的基础链路：

- 主 Agent 支持 `INVENTORY_ANALYSIS` 意图，并能将分析类请求路由到 `InventoryAnalysisNode`；
- `InventoryAnalysisSubAgent` 支持 LLM 在只读 Tool 集合内进行动态、多轮 Tool Calling；
- 当前库存查询能力能够获得总库存、预占库存、冻结库存、可用库存和库位分布；
- 当前 Prompt 已要求不猜测数据、Tool 失败时不伪造结果、证据不足时说明信息缺口；
- ADR-003 已确认 MCP 是正式 Agent Tool 能力边界；
- Java WMS Service 负责确定性库存事实、业务规则、最终权限和数据一致性。

当前实现仍不足以稳定解释“为什么可用库存低”：Repository 中的分析 Tool 尚未通过正式 MCP 链路获取完整证据，输出也缺少统一的事实、可能原因和未知项表达。因此，本需求在严格只读和证据驱动的前提下，增强可用库存偏低原因分析。

## Goal

V1 针对 `AVAILABLE_STOCK_LOW` 提供证据驱动的原因分析：

- 以指定 `materialCode` 为分析对象；
- 收集库存汇总、预占和冻结三类 Evidence；
- 重点调查 `RESERVED_STOCK_HIGH` 和 `FROZEN_STOCK_HIGH`；
- 将输出明确分类为 `FACT`、`POSSIBLE_CAUSE` 和 `UNKNOWN`；
- 同时提供结构化分析结果与自然语言解释；
- 支持受限制但透明的 `PARTIAL` 分析；
- 没有 Java WMS 确定性原因规则时，不把候选原因表述为已确认根因；
- 全程保持只读，不执行任何库存、订单、任务或设备写操作。

## V1 Business Definition

### Supported Anomaly

V1 只支持 `AVAILABLE_STOCK_LOW`。

其他库存异常类型不属于本次交付范围。

### Investigation Focus

V1 重点调查：

- `RESERVED_STOCK_HIGH`
- `FROZEN_STOCK_HIGH`

这两个标识表示 V1 的候选调查方向，不授权 LLM 自行定义“高”的阈值。是否满足确定性“高库存”规则，必须由 Java WMS 返回的确定性事实或规则结果支持。

### Output Classification

V1 对分析内容使用以下分类：

- `FACT`：由 Java WMS Evidence 直接支持的库存事实或确定性规则结果；
- `POSSIBLE_CAUSE`：Evidence 支持其与 `AVAILABLE_STOCK_LOW` 相关，但没有 Java WMS 确定性原因规则确认其为根因；
- `UNKNOWN`：Evidence 缺失、失败、冲突或不足，无法形成受支持的判断。

V1 不使用 LLM 数值置信度或由 LLM 生成的概率分数。

### V1 Evidence Scope

V1 Evidence 范围严格限定为：

- `InventorySummaryEvidence`
- `ReservationEvidence`
- `FreezeEvidence`

任何超出这三类 Evidence 的原因调查不属于 V1。

## Existing Capability and Gap Analysis

### 已有能力

1. `INVENTORY_ANALYSIS` 已存在于意图模型、识别 Prompt、确定性路由和 Main Graph。
2. `InventoryAnalysisSubAgent` 已具备 Tool 白名单、多轮 Tool Calling、异常隔离和最大轮次保护。
3. 当前库存模型包含 `materialCode`、总库存、预占库存、冻结库存和可用库存。
4. 当前库存和库位查询已通过 Port 调用 Java WMS HTTP Adapter。
5. 当前 Prompt 已具备不猜测、不伪造、证据不足时说明缺口等基础约束。
6. 已有 Architecture Test 检查业务层与 Integration 层依赖边界。

### Implementation Gaps

以下均为实现差距，不是需求 Open Question：

1. MCP Server 当前只有返回模拟数据的 `get_stock`，尚未实现 V1 所需的真实 inventory Evidence Tool。
2. `wms_mcp/tools/inventory.py` 与 `wms_mcp/clients/wms_client.py` 当前为空。
3. `InventoryAnalysisSubAgent` 当前绑定进程内 Capability Tool，尚未经过正式 MCP Client 和 MCP Server。
4. 当前 Tool 返回普通字典，尚无统一、可追溯的 Evidence 表达。
5. SubAgent 当前只返回自然语言字符串，尚无结构化分析结果。
6. `InventoryAnalysisNode` 读取 `question`，而现有 State 链路使用 `user_message`，存在问题传递缺口。
7. `INVENTORY_ANALYSIS` 当前无条件通过参数校验，尚未落实 `materialCode` 必填规则和 Request/Session Context 补全行为。
8. 当前错误结果不能稳定区分无数据、无权限、部分成功、超时和上游失败。
9. 当前缺少 InventoryAnalysisSubAgent 自动化测试、MCP Contract Test、Intent Evaluation 和 Agent Evaluation。

## Scope

V1 范围包括：

- 识别针对 `AVAILABLE_STOCK_LOW` 的原因分析请求；
- 以单个 `materialCode` 作为必填业务分析对象；
- 优先从 Request/Session Context 获取 warehouse、tenant、user；必要上下文无法确定时向用户补问；
- 通过 `InventorySummaryEvidence` 获取当前库存汇总事实；
- 通过 `ReservationEvidence` 调查 `RESERVED_STOCK_HIGH`；
- 通过 `FreezeEvidence` 调查 `FROZEN_STOCK_HIGH`；
- 使用 `FACT`、`POSSIBLE_CAUSE`、`UNKNOWN` 分类表达结果；
- 在缺少 Java WMS 确定性原因规则时，将受 Evidence 支持的相关原因保持为 `POSSIBLE_CAUSE`，不得升级为已确认根因；
- 支持 `PARTIAL` 分析，并明确成功调查范围、失败调查范围和结论限制；
- 同时返回结构化分析结果和自然语言解释；
- 结构化结果至少包含 `status`、`subject`、`facts`、`possibleCauses`、`unknowns`、`evidences`、`limitations`；
- 固定采用 `InventoryAnalysisSubAgent → MCP Client → MCP Server → Java WMS API` 调用链；
- 对证据不足、无数据、无权限、冲突、部分失败和完全失败给出不误导的反馈；
- 为后续阶段定义所需的 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation 和 Architecture Rule 验证。

## Out of Scope

- `AVAILABLE_STOCK_LOW` 之外的库存异常类型；
- `RESERVED_STOCK_HIGH` 和 `FROZEN_STOCK_HIGH` 之外的新原因方向；
- `InventorySummaryEvidence`、`ReservationEvidence`、`FreezeEvidence` 之外的订单、波次、任务、批次、库位、质量、出入库或库存流水 Evidence；
- 全仓、多物料、批次、库位、订单或任务级顶层原因分析；
- 由 LLM 定义库存阈值、确定性规则、原因编码或数值置信度；
- 自动冻结、解冻、扣减、调整、移库或处置库存；
- 自动创建、修改或取消订单、出入库单或仓库任务；
- 自动控制仓储设备；
- Agent 或 MCP Server 直接访问数据库；
- 保证在 Evidence 不足时一定找到根因；
- 本 DEFINE Resolution 阶段修改 Prompt、Graph、Node、Tool、MCP、Java API、测试或其他业务代码；
- 本轮进入 DESIGN、G1、IMPLEMENT、VERIFY 或 G2。

## Business Rules

1. V1 仅分析 `AVAILABLE_STOCK_LOW`。
2. V1 重点调查的候选原因仅为 `RESERVED_STOCK_HIGH` 和 `FROZEN_STOCK_HIGH`。
3. `materialCode` 是必填业务参数。
4. warehouse、tenant、user 优先从受信任的 Request/Session Context 获取，不允许由 LLM 猜测或覆盖；无法确定必要上下文时必须补问。
5. V1 Evidence 只允许来自 `InventorySummaryEvidence`、`ReservationEvidence` 和 `FreezeEvidence`。
6. 库存数量、业务状态和确定性原因规则必须由 Java WMS Service 提供；Agent 与 MCP 不得重新计算或创造业务事实。
7. 所有重要事实与原因表达必须有 Evidence 支持；无 Evidence 不得形成确定性结论。
8. 输出分类只能使用 `FACT`、`POSSIBLE_CAUSE`、`UNKNOWN`。
9. Java WMS 返回的库存事实或确定性规则结果归类为 `FACT`。
10. 没有 Java WMS 确定性原因规则时，即使预占或冻结 Evidence 与可用库存偏低相关，也只能归类为 `POSSIBLE_CAUSE`，不得表述为已确认根因。
11. Evidence 缺失、调用失败、结果冲突或信息不足时，受影响的判断必须归类为 `UNKNOWN`。
12. V1 不输出由 LLM 生成的数值置信度、概率或评分。
13. 允许返回 `PARTIAL` 分析，但必须同时说明成功调查范围、失败调查范围和结论限制。
14. 查询失败仅表示未成功获取数据，不等于业务数据不存在，也不等于原因已排除。
15. 结构化分析结果和自然语言解释必须表达一致，不得出现相互矛盾的分类或结论。
16. 结构化结果至少包含 `status`、`subject`、`facts`、`possibleCauses`、`unknowns`、`evidences`、`limitations`；具体字段类型、嵌套结构和错误 Contract 留给 DESIGN。
17. 正式 Agentic 调用链固定为 `InventoryAnalysisSubAgent → MCP Client → MCP Server → Java WMS API`。Repository 未完成该链路属于 Implementation Gap，不再作为需求问题。
18. Java WMS API 负责用户、租户、仓库隔离和最终权限判定；MCP 与 Agent 不得绕过权限校验。
19. 库存异常原因分析是只读能力，不得直接或间接触发任何库存、订单、任务或设备写操作。
20. 如果自然语言解释包含后续建议，必须明确建议尚未执行；任何实际高风险写操作必须另行进入 Proposal、Workflow、Human Approval、受控 MCP Tool 和 Java WMS API 流程。

## Acceptance Criteria

1. 用户请求分析某个物料可用库存偏低原因时，系统将其识别为 `AVAILABLE_STOCK_LOW` 分析；其他异常类型明确返回 V1 不支持，不伪装成已完成分析。
2. 缺少 `materialCode` 时，系统明确补问物料编码，不启动原因分析。
3. warehouse、tenant、user 能从 Request/Session Context 确定时不重复询问；必要上下文无法确定时才补问。
4. 参数和必要上下文完整后，InventoryAnalysisSubAgent 通过固定 MCP 调用链获取 Java WMS Evidence。
5. 分析只使用 `InventorySummaryEvidence`、`ReservationEvidence` 和 `FreezeEvidence`；不调用 V1 范围外的数据源。
6. 系统围绕 `RESERVED_STOCK_HIGH` 和 `FROZEN_STOCK_HIGH` 展开调查，不生成其他原因编码。
7. Java WMS 返回的库存汇总、预占和冻结事实在结构化结果中归入 `FACT`，并可追溯到对应 Evidence。
8. 没有 Java WMS 确定性原因规则时，预占或冻结相关解释最多归入 `POSSIBLE_CAUSE`，自然语言不得称其为已确认根因。
9. Evidence 缺失、失败、冲突或不足时，受影响内容归入 `UNKNOWN`，并说明缺少的信息或失败范围。
10. 输出不包含由 LLM 生成的数值置信度、概率或评分。
11. 部分 Evidence 成功、部分失败时，`status` 能表达 `PARTIAL`，并明确列出成功调查范围、失败调查范围与结论限制。
12. 所有必要 Evidence 都无法获得时，系统不输出确定性或可能原因，明确说明分析无法完成及原因。
13. 结构化结果至少包含 `status`、`subject`、`facts`、`possibleCauses`、`unknowns`、`evidences`、`limitations`。
14. 系统同时提供自然语言解释；自然语言与结构化结果中的事实、可能原因、未知项和限制保持一致。
15. 无权限、租户不匹配或仓库无权访问时，不泄露受限库存数据，并保留 Java WMS API 的最终权限判定。
16. 整个分析流程不调用写 Tool，不修改库存、订单、任务或设备状态。
17. 后续实现必须通过与变更范围匹配的 Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation 和 Architecture Rule 检查。

## Technical Findings / DESIGN Inputs

以下问题属于 HOW，只作为下一轮 DESIGN 输入，不属于需求 Open Question：

1. `InventoryAnalysisNode` 当前读取 `question`，而现有状态链路使用 `user_message`；DESIGN 需统一问题传递字段和多轮上下文策略。
2. `InventorySummaryEvidence`、`ReservationEvidence`、`FreezeEvidence` 的类设计、字段、标识、时间戳、来源、生命周期和序列化方式。
3. MCP inventory tools 的名称、数量、粒度、注册方式以及 Tool 与 Evidence 类型的映射。
4. MCP Client Port、Adapter、连接生命周期和依赖注入方式。
5. Java WMS API 的具体 endpoint、请求/响应字段、分页、错误码和版本策略。
6. Request/Session Context 中 warehouse、tenant、user、requestId 和认证信息的具体传递方式。
7. `status` 除 `PARTIAL` 外的枚举、结构化结果各字段类型、嵌套结构和自然语言渲染方式。
8. 无数据、无权限、超时、非法响应、部分成功和上游不可用的具体错误映射。
9. timeout、retry、circuit breaker、并发、Tool Calling 上限和成本控制参数。
10. Evidence 冲突检测、去重、顺序、脱敏、日志和审计实现。
11. MCP 正式链路与当前进程内 Capability Tool 的迁移和兼容策略。
12. Unit Test、Integration Test、MCP Contract Test、Intent Evaluation、Agent Evaluation、Critical Evaluation 和 Architecture Rule 的具体用例与执行命令。

## Open Questions

无。

当前不存在仍需 Human 决定且会改变 V1 产品行为的 WHAT 类问题；DEFINE 可以保持 `APPROVED`。任何新增异常类型、原因方向、Evidence 类型或分析对象均属于 Scope Change，必须重新进入需求评审。

## DEFINE Resolution Summary

### Closed Open Questions

1. 支持的异常类型：仅 `AVAILABLE_STOCK_LOW`。
2. 重点原因方向：仅 `RESERVED_STOCK_HIGH`、`FROZEN_STOCK_HIGH`。
3. 输出分类：`FACT`、`POSSIBLE_CAUSE`、`UNKNOWN`。
4. 置信度：V1 不使用 LLM 数值置信度。
5. 原因确认边界：没有 Java WMS 确定性原因规则时，不得将 `POSSIBLE_CAUSE` 表述为已确认根因。
6. Evidence 范围：仅 `InventorySummaryEvidence`、`ReservationEvidence`、`FreezeEvidence`。
7. 必填参数与上下文：`materialCode` 必填；warehouse、tenant、user 优先来自 Request/Session Context，必要时补问。
8. 部分成功：允许 `PARTIAL`，但必须披露成功范围、失败范围和结论限制。
9. 响应形态：同时提供结构化结果和自然语言解释，并确定结构化最小字段集合。
10. MCP 定位与调用链：MCP 是正式架构，固定调用链已确认；当前缺失属于 Implementation Gap。

### Moved to DESIGN Inputs

1. `question/user_message` 与多轮上下文的技术处理。
2. 三类 Evidence 的类、字段、ID、时间戳、生命周期和序列化设计。
3. MCP Tool 的组织、命名、粒度和注册方式。
4. MCP Client Port/Adapter、依赖注入和连接生命周期。
5. Java WMS API 和 MCP 的具体 Contract。
6. Request/Session Context 的技术传递方式。
7. 结构化响应的具体类型、嵌套结构和错误模型。
8. timeout、retry、circuit breaker、并发与调用上限。
9. Evidence 冲突、脱敏、日志和审计实现。
10. 测试、Contract Test 与 Evaluation 的具体实现。

### Blocking Business Questions

无。

