# D-001 库存异常原因分析增强 Behaviors

## 说明

本文档仅定义当前需求与架构可以确定的关键行为。

支持的异常类型、原因目录、原因确认规则、证据来源、必填参数、部分成功规则和响应契约仍属于 `requirement.md` 中的 Open Questions。以下行为使用“经批准的原因规则”“经确认的调查范围”和“授权的只读 Tool”描述约束，不预设具体业务规则。

## B1 识别原因分析请求

**Given** 用户明确询问库存异常、异常原因或需要综合多项库存数据进行判断

**When** 主 Agent 识别本轮意图

**Then** 系统将请求识别为库存分析类请求

**And** 将其路由至库存分析能力

**And** 不进入库存写操作流程

## B2 单一事实查询不升级为原因分析

**Given** 用户只要求查询一个明确的库存数量或库位事实

**When** 主 Agent 识别本轮意图

**Then** 系统优先使用对应的确定性查询能力

**And** 不无故启动多轮原因分析

## B3 完整传递用户问题

**Given** 用户提交了库存异常原因分析问题

**When** Main Graph 调用 InventoryAnalysisNode 和 InventoryAnalysisSubAgent

**Then** SubAgent 接收到用户实际提交的分析问题

**And** 不以空字符串或无关历史问题替代本轮问题

## B4 缺少必要调查范围

**Given** 业务已确认某类异常分析的必填参数

**And** 用户请求缺少一个或多个必填参数

**When** 系统校验分析请求

**Then** 系统明确指出缺失参数

**And** 请求用户补充信息

**And** 不生成异常原因结论

## B5 动态收集相关证据

**Given** 请求包含经确认的完整调查范围

**And** 用户有权访问该范围

**When** InventoryAnalysisSubAgent 调查异常原因

**Then** SubAgent 根据问题和已取得的 Evidence 选择必要的只读 Tool

**And** 不要求每次调用所有 Tool

**And** 不调用未授权 Tool

## B6 基于充分证据确认原因

**Given** Java WMS Service 返回的 Evidence 满足经批准的原因确认规则

**When** InventoryAnalysisSubAgent 生成结论

**Then** 回答可以将该原因表述为已确认原因

**And** 关联支撑该原因的关键 Evidence

**And** 保留调查范围和数据时间点

## B7 仅有相关现象时不确认因果

**Given** Tool 结果显示某项库存现象与异常相关

**And** 现有 Evidence 不满足经批准的原因确认规则

**When** InventoryAnalysisSubAgent 解释该现象

**Then** 不将该现象表述为已确认根因

**And** 仅在业务规则允许时将其标识为候选或可能原因

**And** 说明仍需补充的证据

## B8 多个原因同时成立

**Given** Evidence 满足多个经批准的原因规则

**When** InventoryAnalysisSubAgent 输出分析结果

**Then** 系统按照经确认的多原因展示与排序规则输出结果

**And** 每个原因分别关联其 Evidence

**And** 不擅自合并为仓库中未定义的新原因

## B9 未发现可确认原因

**Given** 已成功完成经确认范围内的必要查询

**And** Evidence 不满足任何已批准的原因确认规则

**When** InventoryAnalysisSubAgent 输出结果

**Then** 回答说明当前未确认异常原因

**And** 不声称异常不存在

**And** 说明已调查范围及仍可能缺少的信息

## B10 证据缺失

**Given** 分析所需的一项或多项关键 Evidence 不存在或不可用

**When** InventoryAnalysisSubAgent 尝试形成结论

**Then** 回答将相关结论标识为无法判断

**And** 指出缺少的 Evidence

**And** 不补造库存事实或确定性原因

## B11 证据冲突

**Given** 两项或多项 Evidence 对同一关键事实给出冲突结果

**When** InventoryAnalysisSubAgent 生成分析结果

**Then** 回答明确披露证据冲突

**And** 标明受冲突影响的结论

**And** 不静默选择其中一项作为确定事实

## B12 部分 Tool 查询失败

**Given** 分析过程中部分只读 Tool 成功返回 Evidence

**And** 其他 Tool 失败、超时或返回非法响应

**When** InventoryAnalysisSubAgent 输出结果

**Then** 系统按照经确认的部分成功规则处理

**And** 明确区分已取得证据与未完成调查

**And** 不使用失败查询排除某个原因

## B13 必要 Tool 全部失败

**Given** 支持结论所需的 Tool 均调用失败、超时或返回非法响应

**When** InventoryAnalysisSubAgent 结束本次分析

**Then** 回答明确说明原因分析未成功完成

**And** 不把技术失败解释为无异常或无原因

**And** 不伪造 Tool 结果

## B14 查询成功但无业务数据

**Given** Tool 成功执行

**And** Java WMS API 明确返回经确认调查范围内无匹配业务数据

**When** InventoryAnalysisSubAgent 解释结果

**Then** 回答说明该调查范围内没有匹配数据

**And** 将其与 Tool 失败明确区分

**And** 不把无数据自动解释为异常不存在

## B15 无访问权限

**Given** 用户无权访问请求中的租户、仓库、货主或库存范围

**When** Java WMS API 执行最终权限校验

**Then** 系统拒绝返回受限 Evidence

**And** Agent 不通过其他 Tool 绕过权限校验

**And** 回答不泄露受限范围内是否存在库存或异常

## B16 超过 Tool Calling 上限

**Given** InventoryAnalysisSubAgent 已达到配置的最大 Tool Calling 轮次

**And** 当前 Evidence 仍不足以完成原因分析

**When** SubAgent 终止分析

**Then** 回答说明分析因调用上限和证据不足而终止

**And** 说明已知事实和仍缺少的信息

**And** 不继续无限调用 Tool

## B17 分析全程保持只读

**Given** InventoryAnalysisSubAgent 正在调查库存异常原因

**When** SubAgent 选择并调用 Tool

**Then** 只允许调用显式授权的只读查询 Tool

**And** 不调用冻结、解冻、扣减、调整、移库、出入库确认或设备控制 Tool

## B18 输出区分事实、结论、推断和未知

**Given** 本次调查取得了一项或多项 Evidence

**When** InventoryAnalysisSubAgent 生成最终回答

**Then** 回答区分 Tool 返回的业务事实

**And** 区分由确定性规则给出的结论

**And** 区分基于 Evidence 的推断

**And** 明确标识未知或无法判断的信息

## B19 结论可追溯

**Given** 最终回答包含重要库存事实或原因结论

**When** 用户或审计人员复核本次分析

**Then** 每项重要结论能够关联一个或多个 Evidence

**And** Evidence 能识别数据来源、查询范围、状态和适用的数据时间点

## B20 只提出未执行建议

**Given** 分析结果支持提出后续处理建议

**When** InventoryAnalysisSubAgent 向用户回答

**Then** 回答明确说明建议尚未执行

**And** 不声称库存、订单、任务或设备状态已经改变

**And** 任何高风险写操作必须进入独立的 Proposal、Workflow 和 Human Approval 流程

