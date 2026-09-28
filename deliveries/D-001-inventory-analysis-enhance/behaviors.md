# D-001 库存异常原因分析增强 Behaviors

## Status

- 阶段：DEFINE
- DEFINE Resolution：完成
- 状态：APPROVED
- DESIGN：PAUSED

## V1 Behavior Boundary

V1 只支持 `AVAILABLE_STOCK_LOW`，只调查 `RESERVED_STOCK_HIGH` 和 `FROZEN_STOCK_HIGH`，只使用 `InventorySummaryEvidence`、`ReservationEvidence` 和 `FreezeEvidence`。

所有输出内容只允许分类为 `FACT`、`POSSIBLE_CAUSE` 或 `UNKNOWN`。V1 不使用 LLM 数值置信度。

## B1 识别 V1 支持的异常分析请求

**Given** 用户请求分析指定物料可用库存偏低的原因

**And** 请求包含 `materialCode` 或可通过补问取得 `materialCode`

**When** 主 Agent 识别本轮意图

**Then** 系统将请求识别为 `AVAILABLE_STOCK_LOW` 库存分析请求

**And** 将其交给 InventoryAnalysisSubAgent

**And** 不进入库存写操作流程

## B2 拒绝 V1 范围外的异常类型

**Given** 用户请求分析的库存异常不是 `AVAILABLE_STOCK_LOW`

**When** 系统判断 V1 支持范围

**Then** 系统明确说明该异常类型不在 V1 范围内

**And** 不使用 `AVAILABLE_STOCK_LOW` 的分析结果替代用户请求

**And** 不生成范围外的原因结论

## B3 缺少 materialCode

**Given** 用户请求分析 `AVAILABLE_STOCK_LOW`

**And** 当前请求与会话上下文都没有 `materialCode`

**When** 系统校验业务参数

**Then** 系统明确补问 `materialCode`

**And** 不启动原因分析

**And** 不猜测物料编码

## B4 从受信任上下文获取分析范围

**Given** 用户已提供 `materialCode`

**And** warehouse、tenant、user 可以从受信任的 Request/Session Context 获取

**When** 系统准备原因分析请求

**Then** 系统使用受信任上下文中的 warehouse、tenant、user

**And** 不要求用户重复提供已确定的信息

**And** 不允许 LLM 覆盖这些上下文

## B5 必要上下文无法确定

**Given** 用户已提供 `materialCode`

**And** 执行分析所需的 warehouse、tenant 或 user 无法从 Request/Session Context 确定

**When** 系统准备原因分析请求

**Then** 系统只补问无法确定的必要上下文

**And** 在上下文补全前不查询受限库存数据

## B6 通过正式 MCP 链路收集 Evidence

**Given** `materialCode` 和必要 Request/Session Context 已完整

**When** InventoryAnalysisSubAgent 调查 `AVAILABLE_STOCK_LOW`

**Then** 调用链必须为 `InventoryAnalysisSubAgent → MCP Client → MCP Server → Java WMS API`

**And** 不绕过 MCP Server 直接访问 Java WMS API

**And** Agent 与 MCP Server 都不访问数据库

## B7 限定 V1 Evidence 范围

**Given** InventoryAnalysisSubAgent 正在调查 `AVAILABLE_STOCK_LOW`

**When** SubAgent 选择调查 Evidence

**Then** 只允许使用 `InventorySummaryEvidence`、`ReservationEvidence` 和 `FreezeEvidence`

**And** 不调用订单、任务、批次、库位、质量、出入库或库存流水 Evidence

## B8 输出库存汇总事实

**Given** Java WMS API 成功返回 `InventorySummaryEvidence`

**When** 系统生成结构化分析结果和自然语言解释

**Then** Evidence 直接支持的库存汇总信息归类为 `FACT`

**And** 事实可以追溯到 `InventorySummaryEvidence`

**And** Agent 不重新计算或修改 Java WMS 返回的库存数量

## B9 调查 RESERVED_STOCK_HIGH

**Given** Java WMS API 成功返回 `ReservationEvidence`

**When** InventoryAnalysisSubAgent 调查 `RESERVED_STOCK_HIGH`

**Then** 预占数量和预占业务事实归类为 `FACT`

**And** Java WMS 未提供确定性原因规则结果时，预占相关解释最多归类为 `POSSIBLE_CAUSE`

**And** 不将其表述为已确认根因

## B10 调查 FROZEN_STOCK_HIGH

**Given** Java WMS API 成功返回 `FreezeEvidence`

**When** InventoryAnalysisSubAgent 调查 `FROZEN_STOCK_HIGH`

**Then** 冻结数量和冻结业务事实归类为 `FACT`

**And** Java WMS 未提供确定性原因规则结果时，冻结相关解释最多归类为 `POSSIBLE_CAUSE`

**And** 不将其表述为已确认根因

## B11 Java WMS 提供确定性规则结果

**Given** Java WMS API 返回其确定性业务规则产生的原因判断

**When** InventoryAnalysisSubAgent 解释该结果

**Then** 该确定性规则结果作为 `FACT` 展示

**And** 明确其来源为 Java WMS Evidence

**And** Agent 不改变该规则结果

## B12 不输出 LLM 数值置信度

**Given** InventoryAnalysisSubAgent 正在生成原因分析

**When** 输出结构化结果或自然语言解释

**Then** 不输出由 LLM 生成的数值置信度、概率或评分

**And** 不使用数值分数暗示原因已经确认

## B13 Evidence 不足时输出 UNKNOWN

**Given** 任一调查方向缺少必要 Evidence、Evidence 冲突或 Evidence 不足以支持相关解释

**When** InventoryAnalysisSubAgent 生成结果

**Then** 受影响的内容归类为 `UNKNOWN`

**And** 说明缺失、冲突或不足的 Evidence

**And** 不补造库存事实或原因

## B14 部分分析成功

**Given** 三类 V1 Evidence 中至少一类成功返回

**And** 至少一类 Evidence 获取失败或不可用

**When** InventoryAnalysisSubAgent 输出分析结果

**Then** 结构化结果的 `status` 表达 `PARTIAL`

**And** 明确列出成功调查范围

**And** 明确列出失败调查范围

**And** 在 `limitations` 中说明失败对结论的限制

**And** 不使用失败范围确认或排除原因

## B15 所有必要 Evidence 均不可用

**Given** `InventorySummaryEvidence`、`ReservationEvidence` 和 `FreezeEvidence` 均无法取得有效结果

**When** InventoryAnalysisSubAgent 结束分析

**Then** 不输出 `POSSIBLE_CAUSE`

**And** 将无法判断的信息归入 `UNKNOWN`

**And** 明确说明分析未能完成及失败范围

## B16 无业务数据与技术失败分离

**Given** Java WMS API 明确返回无匹配业务数据，或者 Tool 调用发生技术失败

**When** 系统生成结果

**Then** 无业务数据与技术失败使用不同的状态或错误表达

**And** 不把技术失败解释为业务数据不存在

**And** 不把无数据自动解释为原因已排除

## B17 同时返回结构化结果和自然语言解释

**Given** InventoryAnalysisSubAgent 完成本次分析

**When** 系统返回响应

**Then** 响应同时包含结构化分析结果和自然语言解释

**And** 结构化结果至少包含 `status`、`subject`、`facts`、`possibleCauses`、`unknowns`、`evidences`、`limitations`

**And** 两种表达中的事实、可能原因、未知项和限制保持一致

## B18 输出只使用三种分类

**Given** 分析结果包含库存事实、原因解释或未知信息

**When** 系统为结果内容分类

**Then** 只使用 `FACT`、`POSSIBLE_CAUSE`、`UNKNOWN`

**And** 不生成 `CONFIRMED_CAUSE` 或其他未批准分类

## B19 权限不足时不泄露 Evidence

**Given** Java WMS API 判定 user、tenant 或 warehouse 无权访问目标库存

**When** 系统处理权限失败

**Then** 不返回受限的库存数量、预占、冻结或原因信息

**And** Agent 不通过其他调用绕过权限校验

## B20 分析过程保持只读

**Given** InventoryAnalysisSubAgent 正在调查 `AVAILABLE_STOCK_LOW`

**When** SubAgent 选择并调用能力

**Then** 只允许调用只读查询能力

**And** 不调用冻结、解冻、扣减、调整、移库、出入库确认、任务修改或设备控制能力

## B21 建议不等于执行

**Given** 自然语言解释包含后续处理建议

**When** 系统向用户返回建议

**Then** 明确说明建议尚未执行

**And** 不声称库存、订单、任务或设备状态已经改变

**And** 任何高风险写操作必须进入独立的 Proposal、Workflow 和 Human Approval 流程

