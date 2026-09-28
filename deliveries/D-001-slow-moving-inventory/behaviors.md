# D-001 库存积压分析 Behaviors

## 说明

本文档只定义当前能够由需求与架构确定的关键行为。

积压定义、判定阈值、等级、时间窗口、分析粒度、必填参数和返回字段仍属于 `requirement.md` 中的 Open Questions。本文使用“经批准的积压规则”和“经确认的查询范围”作为占位约束，不预设具体业务值。

## B1 识别库存积压分析诉求

**Given** 用户明确请求分析库存是否积压、积压范围或积压原因

**When** 主 Agent 识别本轮用户意图

**Then** 系统将请求识别为库存分析类请求

**And** 不将其作为普通库存数量查询直接回答

**And** 不进入任何库存写操作流程

## B2 缺少必填查询范围

**Given** 业务已确认库存积压分析的必填参数

**And** 用户请求中缺少其中一个或多个参数

**When** 系统校验分析请求

**Then** 系统明确指出缺少的参数

**And** 请求用户补充信息

**And** 不调用库存积压分析 Tool

## B3 使用确定性积压判定

**Given** 用户提供了经确认的完整查询范围

**And** 用户有权访问该范围

**And** Java WMS Service 已按照经批准的积压规则返回结构化判定与证据

**When** InventoryAnalysisSubAgent 生成分析结论

**Then** Agent 使用 Tool 返回的积压判定

**And** Agent 不自行计算或改变积压状态、等级或确定性指标

**And** Agent 在回答中关联支撑结论的关键证据

## B4 在查询范围内发现积压库存

**Given** 只读积压分析 Tool 返回一个或多个被 Java WMS Service 判定为积压的库存项

**When** InventoryAnalysisSubAgent 解释结果

**Then** 回答明确说明哪些库存项被判定为积压

**And** 回答说明本次查询范围和统计口径

**And** 回答展示 Tool 返回的关键判定证据

**And** 不把未查询范围包含在结论中

## B5 在查询范围内没有积压库存

**Given** 只读积压分析 Tool 成功完成查询

**And** Tool 明确返回经确认的查询范围内没有积压库存

**When** InventoryAnalysisSubAgent 解释结果

**Then** 回答说明“当前查询范围内未发现积压库存”

**And** 不声称其他仓库、物料、货主或时间范围也没有积压库存

## B6 证据不足无法判定

**Given** Tool 返回的事实缺少经批准规则所要求的一个或多个关键证据

**When** InventoryAnalysisSubAgent 尝试分析积压状态

**Then** 回答明确说明当前无法判定

**And** 指出缺失或不可用的证据

**And** 不猜测积压状态、等级、数量或原因

## B7 无历史数据或日期缺失

**Given** 查询结果中存在无库存历史、关键日期缺失或其他无法应用经批准规则的数据项

**When** Java WMS Service 返回这些数据项的确定性处理状态

**Then** InventoryAnalysisSubAgent 按 Tool 返回的状态进行解释

**And** 不自行把该状态解释为“积压”或“不积压”

## B8 Tool 或上游服务失败

**Given** MCP Tool、MCP Server 或 Java WMS API 调用失败、超时或返回格式异常

**When** InventoryAnalysisSubAgent 接收失败结果

**Then** 回答明确说明本次分析未成功完成

**And** 不伪造库存数据

**And** 不把技术失败表述为“没有积压库存”

## B9 无访问权限

**Given** 用户无权访问请求中的租户、仓库、货主或库存范围

**When** Java WMS API 执行最终权限校验

**Then** 系统拒绝返回受限库存数据

**And** Agent 不通过其他 Tool 绕过权限校验

**And** 回答不泄露受限范围内是否存在库存或积压库存

## B10 分析过程保持只读

**Given** InventoryAnalysisSubAgent 正在执行库存积压分析

**When** SubAgent 选择和调用 Tool

**Then** 只允许调用已授权的只读查询 Tool

**And** 不调用库存冻结、解冻、扣减、调整、移库、出入库确认或设备控制 Tool

## B11 分析产生处置建议

**Given** 分析结论表明某些库存可能需要补货调整、调拨、促销、报废或其他处置

**When** InventoryAnalysisSubAgent 向用户回答

**Then** 回答可以在证据支持范围内提出建议

**And** 明确说明建议尚未执行

**And** 不声称库存或业务状态已经改变

**And** 任何后续高风险写操作必须进入独立的 Proposal、Workflow 和 Human Approval 流程

## B12 区分可用库存风险与库存积压

**Given** 当前系统已有基于 `availableRate` 的库存可用量风险定义

**And** 用户请求库存积压分析

**When** 系统执行积压判定和解释

**Then** 不使用 `availableRate` 风险等级替代积压判定

**And** 仅在 Tool 分别提供两类结果时，才分别解释可用库存风险与积压状态

## B13 保留分析范围和数据时点

**Given** Tool 返回积压分析结果及其查询范围、统计口径和数据时间点

**When** InventoryAnalysisSubAgent 输出结论

**Then** 回答保留这些限定信息

**And** 不把某一时点或某一统计窗口的结论描述为永久事实

## B14 多轮 Tool Calling 仍无法取得充分证据

**Given** InventoryAnalysisSubAgent 已调用允许的只读 Tool

**And** 达到最大 Tool Calling 轮次后仍没有充分证据

**When** SubAgent 结束分析

**Then** 回答说明分析因证据不足而终止

**And** 说明仍需补充的信息

**And** 不生成确定的积压结论

