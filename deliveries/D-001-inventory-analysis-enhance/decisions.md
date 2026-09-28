# D-001 库存异常原因分析增强 Architecture Decisions

## Status

- 阶段：DESIGN
- DEFINE：APPROVED
- DESIGN：待 G1 审批
- 实现授权：无

## Decision Summary

本设计复用现有 `INVENTORY_ANALYSIS` 与 `InventoryAnalysisSubAgent`，将分析型查询迁移到正式 MCP 调用链，引入统一 Evidence Envelope，并把确定性原因认定保留在 Java WMS。第一期只支持单物料分析，增强预占、冻结、库存组成与库位四类证据，不引入业务阈值或数值置信度。

## D1 复用现有库存分析意图与 SubAgent

### Options

A. 为原因分析新增 Intent 和 SubAgent

B. 复用 `INVENTORY_ANALYSIS` 和 `InventoryAnalysisSubAgent`

C. 将原因分析实现为固定 Workflow

### Decision

选择 B。

### Reason

现有库存分析已具备动态 Tool 选择和多轮推理边界，符合 ADR-002。原因调查的调用路径会随证据变化，不适合固定 Workflow；新增 SubAgent 会造成职责重复。

### Consequence

意图 Prompt 只需补充评测样例，不新增 IntentType。单一库存或库位查询继续走固定 Node/Capability。

## D2 第一阶段采用单物料调查范围

### Decision

`material_code` 是原因分析唯一由用户提供的必填业务参数。租户、用户和仓库范围从受信任的请求上下文传递，不允许 LLM 构造。第一阶段不支持全仓、多物料、批次、订单或任务作为顶层调查对象。

### Reason

现有意图模型和库存能力以物料编码为主键。单物料范围能形成最小可验证闭环，同时避免在没有业务规则时扩张范围。

### Consequence

用户仅说“库存异常”且没有物料编码时必须补问。后续扩展其他调查对象需要新的交付和契约版本。

## D3 统一使用 `user_message` 传递本轮问题

### Decision

`AgentState.user_message` 是本轮原始问题的唯一规范字段。`InventoryAnalysisNode` 从该字段读取并传给 SubAgent，不新增或继续使用 `question` 字段。

### Reason

当前入口、意图识别和 State 已使用 `user_message`，而 `question` 没有赋值路径。统一字段可修复空问题风险，且不引入重复状态。

## D4 分析型 Tool 使用正式 MCP 调用链

### Decision

InventoryAnalysisSubAgent 的 Tool 调用链采用：

```text
InventoryAnalysisSubAgent
→ MCP Inventory Port
→ MCP Client Adapter
→ MCP Server
→ WMS API Client
→ Java WMS API
```

固定的 `QUERY_STOCK`、`QUERY_LOCATION` Node 继续使用 Capability/Service/Port，不强制迁移到 MCP。

### Reason

符合 ADR-001、ADR-003 和 ADR-005：动态 Tool Calling 通过 MCP 暴露，固定确定性查询保留 Capability。

## D5 第一阶段只提供四个只读 MCP Tool

### Decision

InventoryAnalysisSubAgent 的 Tool 白名单固定为：

1. `inventory_detail_query`
2. `inventory_reservation_query`
3. `inventory_freeze_query`
4. `location_query`

不向该 SubAgent 注册任何写 Tool。

### Reason

库存组成、预占、冻结和库位是现有代码与需求直接提到的最小证据集合。订单、任务、流水、批次和质量等能力留待独立需求扩展，避免本次设计无限扩大。

### Consequence

超出四类证据能够证明的原因必须返回未知或候选原因，不得猜测。

## D6 使用统一 Evidence Envelope

### Decision

所有分析型 MCP Tool 返回同一顶层结构：

- `evidenceId`
- `tool`
- `status`
- `source`
- `query`
- `data`
- `error`
- `observedAt`
- `requestId`

`status` 仅允许：`SUCCESS`、`NO_DATA`、`PARTIAL`、`FORBIDDEN`、`ERROR`。

### Reason

统一结构使 SubAgent 能区分无数据与失败，并将结论关联到具体证据，落实 Evidence-Driven 原则。

### Consequence

MCP Server 负责包装协议与错误，不负责生成业务原因。`evidenceId` 由 MCP Server 生成并在一次请求内唯一。

## D7 原因认定由 Java WMS 给出，Agent 不计算数值置信度

### Decision

Java WMS 可以在 Tool 数据中返回 `assessments`，其 `certainty` 只允许：

- `CONFIRMED`
- `EXCLUDED`
- `UNKNOWN`

Agent 可以根据成功 Evidence 将未被 WMS 确认的相关事实描述为 `POSSIBLE`，但必须明确是候选解释并引用 Evidence。Agent 不生成数值置信度，不得把 `POSSIBLE` 提升为 `CONFIRMED`。

### Reason

确定性原因规则归 Java WMS；当前没有批准的评分模型。取消数值置信度可避免制造虚假精确度。

## D8 多原因全部展示，不由 LLM 自主排序

### Decision

多个 `CONFIRMED` 原因全部展示。若 Java WMS 返回 `priority`，按升序展示；没有 `priority` 时保持 Tool 返回顺序并声明未排序。Agent 不自行选择“主因”。

### Reason

当前没有业务批准的原因优先级，静默选主因会丢失证据。

## D9 允许部分分析，但限制确定性结论

### Decision

至少一个 Tool 成功而其他 Tool 失败时，分析状态为 `PARTIAL`。成功 Evidence 可用于陈述事实；只有 Java WMS 已在成功 Evidence 中返回的 `CONFIRMED`/`EXCLUDED` assessment 可以保持确定性。失败维度必须列为未完成调查，不能用于排除原因。

全部必要 Tool 失败时状态为 `FAILED`，不得输出原因结论。

### Reason

该策略兼顾可用性与事实边界，并覆盖 behaviors B12、B13。

## D10 错误分类在 MCP 边界统一

### Decision

MCP 将错误映射为以下稳定代码：

- `INVALID_ARGUMENT`
- `NOT_FOUND`
- `FORBIDDEN`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `UPSTREAM_INVALID_RESPONSE`
- `INTERNAL_ERROR`

HTTP 404 映射为 `NO_DATA/NOT_FOUND`；401/403 映射为 `FORBIDDEN`；超时、连接失败、5xx 与响应解析失败映射为 `ERROR`。不得把技术失败映射为 `NO_DATA`。

## D11 保持 8 轮上限并采用受控只读重试

### Decision

- SubAgent 最大 Tool Calling 轮次保持 8；
- Java WMS 单次 HTTP 超时沿用 `WMS_SERVICE_TIMEOUT`，默认 10 秒；
- MCP WMS Client 对超时、连接失败、502、503、504 最多重试 1 次；
- 400、401、403、404、409、422 不重试；
- 重试复用同一 `requestId`；
- MCP Client 必须具备可配置熔断器，默认连续 5 次可重试失败后打开 30 秒。

### Reason

查询是只读操作，可以进行有限技术重试；上限、超时和熔断满足 ADR-003 的可用性治理要求，同时避免无限消耗。

## D12 请求身份与审计上下文不得来自模型参数

### Decision

`Authorization`、`requestId`、`userId`、`tenantId`、`warehouseId` 由 Web/API 受信任上下文注入 MCP Adapter，并原样转发给 MCP Server 和 Java WMS。Tool schema 不向 LLM 暴露这些字段。

日志记录 Tool、Evidence ID、请求上下文、耗时、状态和错误码；Token、业务引用等敏感字段必须脱敏。

### Reason

模型不得选择租户、仓库或用户身份；最终权限仍由 Java WMS 判断。

## D13 SubAgent 输出采用结构化内部结果与兼容文本回答

### Decision

SubAgent 内部返回 `InventoryAnalysisResult`：

- `status`: `SUCCESS | PARTIAL | FAILED | INSUFFICIENT_EVIDENCE`
- `answer`: 用户可读文本
- `evidence_ids`: 使用过的 Evidence ID 列表
- `confirmed_causes`: 已确认原因列表
- `possible_causes`: 候选原因列表
- `unknowns`: 未知或未完成项列表

Node 继续把 `answer` 写入现有响应字段，同时把状态和 Evidence ID 写入 AgentState，保持现有客户端兼容。

### Reason

纯字符串无法满足可追溯性；保留 `answer` 可避免不必要地破坏现有 Chat API。

## D14 测试采用分层契约与 Evaluation

### Decision

- Java WMS：确定性原因规则 Unit Test；
- MCP：Tool schema、协议转换、错误映射、身份透传 Contract Test；
- Backend：Node、MCP Adapter、SubAgent 行为 Unit Test；
- Integration：SubAgent → MCP → Fake WMS API；
- Intent Evaluation：分析请求与单一查询的路由区分；
- Agent Evaluation：证据充分、证据不足、冲突、部分失败、无权限、调用上限和禁止写 Tool；
- Architecture Test：应用层不得直接依赖 Integration，MCP 不得访问数据库。

### Reason

满足 AGENTS.md Definition of Done，并让行为与架构约束可执行验证。

## G1 Entry Conditions

进入 G1 前必须确认：

1. `contracts.md` 中的 Java WMS API 和 MCP Tool 契约可由相关系统实现；
2. 四个 Tool 的第一期范围被接受；
3. Evidence Envelope、错误码和原因确定性语义被接受；
4. 身份上下文来源和转发方式被安全评审接受；
5. `tasks.md` 覆盖 requirement、behaviors 与 Definition of Done；
6. 不存在未批准的业务规则或 Scope Change。

