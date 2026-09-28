# 库存异常原因分析增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 实现只针对 `AVAILABLE_STOCK_LOW`、通过正式 MCP 链路收集三类 Evidence、同时返回结构化结果与自然语言解释的只读原因分析能力。

**Architecture:** 复用现有 Main Graph、`INVENTORY_ANALYSIS`、InventoryAnalysisNode 和 InventoryAnalysisSubAgent。SubAgent 只选择三个 READ Tool；MCP Server 调用 Java WMS；确定性 Result Assembler 将 Evidence 映射为 FACT、POSSIBLE_CAUSE、UNKNOWN，Renderer 从结构化结果生成 answer。

**Tech Stack:** Python、LangGraph、LangChain Tool Calling、MCP Python SDK、FastAPI、httpx、Pydantic 2、pytest；外部 Java WMS REST API。

**Spec:** `deliveries/D-001-inventory-analysis-enhance/requirement.md`、`behaviors.md`、`decisions.md`、`contracts.md`

## Global Constraints

- 只有 G1 APPROVED 后才能进入 IMPLEMENT。
- 不允许扩大 V1 异常、原因或 Evidence 范围。
- 不允许 Agent、MCP、LLM 访问数据库或实现库存确定性规则。
- 不允许向 InventoryAnalysisSubAgent 注入写 Tool。
- 不允许由 LLM 输出数值置信度。
- 所有业务代码修改必须先写失败测试；代码注释使用中文。

## Review Focus

1. 缺少可信 user/tenant 时必须 fail closed，不能接受自然语言冒充身份——T1、T3。
2. `question`/`user_message` 修正不能破坏多轮 materialCode 合并——T1、T7。
3. 404 无数据与 timeout/5xx 必须分离——T4、T5。
4. PARTIAL 或冲突不得生成无证据 possibleCause——T2、T6。
5. Tool 白名单必须在装配阶段拒绝写 Tool——T5、T10。

---

## T1 — State、Request Context 与参数校验

**Goal:** 建立受信任 Request/Session Context，统一使用 `user_message`，落实 materialCode 必填。

**修改范围:**

- `backend/wms_agent/apps/warehouse/agent/state/agent_state.py`
- 新增 `backend/wms_agent/apps/warehouse/models/request_context.py`
- `backend/wms_agent/apps/warehouse/api/dependencies.py`
- `backend/wms_agent/apps/warehouse/api/chat_controller.py`
- `backend/wms_agent/apps/warehouse/api/agent_stream_router.py`
- `backend/wms_agent/apps/warehouse/agent/service.py`
- `backend/wms_agent/apps/warehouse/agent/nodes/agent/parameter_validation.py`
- `backend/wms_agent/apps/warehouse/agent/nodes/agent/inventory_analysis.py`

**Dependencies:** 无。

**Acceptance Criteria:**

- AgentState 保存可序列化 request_context，但不保存 authorization；
- InventoryAnalysisNode 使用当前轮 `user_message`，不读取 `question`；
- INVENTORY_ANALYSIS 缺少 materialCode 时进入 clarification；
- user/tenant 缺失时要求恢复可信 Session；warehouse 缺失时进入受控补全；
- 非分析流程行为不变。

**Test / Evaluation Requirements:**

- Unit Test：RequestContext 校验、State 序列化、参数补问、Node 问题传递；
- Regression：context merge、QUERY_STOCK、QUERY_LOCATION、FREEZE_INVENTORY；
- Critical：自然语言中的 tenant/user 不得覆盖可信上下文。

## T2 — Evidence Model、Result Assembler 与 Renderer

**Goal:** 实现三类 Evidence、分类项、冲突检测、Result 状态聚合和确定性 answer 渲染。

**修改范围:**

- 新增 `backend/wms_agent/apps/warehouse/models/evidence.py`
- 新增 `backend/wms_agent/apps/warehouse/models/inventory_analysis.py`
- 新增 `backend/wms_agent/apps/warehouse/services/inventory_analysis_result_assembler.py`
- 新增 `backend/wms_agent/apps/warehouse/services/inventory_analysis_answer_renderer.py`

**Dependencies:** T1 的 RequestContext/Request Contract。

**Acceptance Criteria:**

- 只支持 `InventorySummaryEvidence`、`ReservationEvidence`、`FreezeEvidence` 三类 Evidence 与 `FACT`、`POSSIBLE_CAUSE`、`UNKNOWN` 三种 classification；
- dangling evidence reference 验证失败；
- Java WMS CONFIRMED assessment 映射为 FACT；未确认候选只能映射为 POSSIBLE_CAUSE；
- Evidence 缺失、失败、冲突映射为 UNKNOWN；
- SUCCESS/PARTIAL/FAILED 按 contracts.md 聚合；
- answer 完全从结构化 Result 渲染且无数值置信度。

**Test / Evaluation Requirements:**

- Unit Test：所有 enum、跨字段校验、PARTIAL、全失败、NO_DATA、VALUE_CONFLICT、TEMPORAL_CONFLICT；
- Property/parameterized tests：每个分类项引用存在且 analysisId 一致；
- Critical：POSSIBLE_CAUSE 文案不得出现“已确认根因”。

## T3 — Java WMS V1 查询能力

**Goal:** 由 Java WMS 提供三类只读 Evidence 数据、确定性 assessment、权限与规则版本。

**修改范围:**

- 外部 Java WMS Repository 的 Controller、DTO、Service、权限校验与 Unit/Provider Contract Test；当前工作区不包含 Java 源码。

**Dependencies:** contracts.md 第 6–10 节。

**Acceptance Criteria:**

- 提供三个只读 logical API；
- 每个 API 执行 Authentication、Authorization、Tenant、Warehouse 校验；
- 返回 inventoryVersion、observedAt、unit、assessment、ruleVersion；
- 所有 LOW/HIGH 与因果确认规则位于 Java Service；
- 无任何写副作用。

**Test / Evaluation Requirements:**

- Java Unit Test：AVAILABLE_STOCK_LOW、RESERVED_STOCK_HIGH、FROZEN_STOCK_HIGH 的边界由 Java 团队既有业务规则验证；
- Provider Contract Test：200、404、400/422、401/403、5xx、schema；
- Security Test：跨 tenant/warehouse 拒绝且不泄露数据；
- G2 必须附外部构建标识和测试证据。

## T4 — MCP Server、WMS Client 与三个 READ Tool

**Goal:** 实现 MCP Server → Java WMS 的真实只读 Evidence 适配。

**修改范围:**

- `mcp-server/wms_mcp/clients/wms_client.py`
- `mcp-server/wms_mcp/tools/inventory.py`
- `mcp-server/wms_mcp/server.py`
- 新增 `mcp-server/wms_mcp/models/evidence.py`
- 新增 `mcp-server/wms_mcp/config.py`
- `mcp-server/.env.example`

**Dependencies:** T3 Provider Contract；可先使用严格 MockTransport。

**Acceptance Criteria:**

- 只注册三个 V1 READ Tool；
- 输入只暴露 material_code；可信上下文作为传输元数据；
- 返回统一 Evidence Contract，不返回自由字符串；
- 正确映射 NO_DATA、FORBIDDEN、FAILED；
- timeout/retry/circuit breaker 符合 decisions.md；
- MCP 包无数据库依赖。

**Test / Evaluation Requirements:**

- MCP Contract Test：Tool discovery、input/output schema、三类 Evidence；
- Client Unit Test：URL encode、身份转发、timeout、单次 retry、不可重试状态、熔断；
- Security Test：authorization 不出现在日志和 Tool output；
- Architecture Test：禁止数据库 Driver/Repository。

## T5 — Backend MCP Client Port、Adapter 与安全 Tool Registry

**Goal:** 实现 InventoryAnalysisSubAgent → MCP Client，并在组合根安全注入 Tool。

**修改范围:**

- 新增 `backend/wms_agent/apps/warehouse/ports/inventory_evidence.py`
- 新增 `backend/wms_agent/integrations/mcp/` Adapter、配置和生命周期文件
- `backend/wms_agent/bootstrap.py`
- `backend/wms_agent/config.py`
- `backend/.env.example`
- `backend/wms_agent/apps/warehouse/container.py`
- `backend/wms_agent/apps/warehouse/agent/container.py`

**Dependencies:** T1、T2、T4。

**Acceptance Criteria:**

- Application 只依赖 InventoryEvidencePort，不 import MCP SDK/Integration；
- Adapter 转发可信上下文，不把其暴露给 LLM；
- Tool Registry 精确等于三个白名单 Tool；
- 写 Tool、未知 Tool、缺少 Tool 时启动失败；
- MCP 连接由 Runtime 生命周期管理并正确关闭；
- 现有固定查询 Capability 保持不变。

**Test / Evaluation Requirements:**

- Unit Test：Port/Adapter mapping、重复 Tool 缓存、上下文缺失 fail closed；
- Resource Lifecycle Test：正常关闭与启动失败清理；
- Architecture Test：apps 不依赖 integrations/MCP SDK；
- Critical：写 Tool 无法被绑定给模型。

## T6 — InventoryAnalysisSubAgent 与 Prompt

**Goal:** 让 SubAgent 在 8 轮内仅规划三类 Evidence 查询，并输出结构化 Result。

**修改范围:**

- `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/agent.py`
- `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/prompt.py`
- `backend/wms_agent/apps/warehouse/agent/nodes/agent/inventory_analysis.py`

**Dependencies:** T2、T5。

**Acceptance Criteria:**

- `ainvoke` 接收 InventoryAnalysisRequest，返回 InventoryAnalysisResult；
- Prompt 只包含 Scope、Tool 选择、安全和停止规则，不包含库存阈值；
- ToolMessage 使用标准 JSON；
- 同一 Tool 一次分析最多真实查询一次；
- 8 轮、30 秒、熔断均能安全降级；
- Result 由 Assembler 生成，answer 由 Renderer 生成；
- 不输出 LLM 数值置信度。

**Test / Evaluation Requirements:**

- Unit Test：调用顺序、无 Tool、未知 Tool、重复 Tool、8 轮、deadline、PARTIAL、全失败；
- Agent Evaluation：FACT/POSSIBLE_CAUSE/UNKNOWN 与自然语言一致；
- Critical：模型尝试调用写 Tool、创造原因编码或确认根因时被拒绝。

## T7 — Structured Result API、SSE 与兼容性

**Goal:** 在保留 answer 的同时向 HTTP/SSE 返回可选 analysisResult。

**修改范围:**

- `backend/wms_agent/apps/warehouse/api/dto/chat.py`
- `backend/wms_agent/apps/warehouse/api/chat_controller.py`
- `backend/wms_agent/apps/warehouse/api/agent_stream_router.py`
- 相关前端 TypeScript 类型仅在需要消费 analysisResult 时单独评审；本 Task 不改变 UI 行为。

**Dependencies:** T1、T2、T6。

**Acceptance Criteria:**

- ChatResponse 对分析请求同时返回 answer 与 analysisResult；
- 非分析响应 analysisResult 为 null；
- SSE done 事件可携带 analysisResult；
- 旧客户端继续只依赖 answer；
- 结构化结果与 answer 一致。

**Test / Evaluation Requirements:**

- API Test：分析/非分析序列化、camelCase、可选字段；
- SSE Integration Test：analysisResult 与同一 requestId；
- Regression：冻结审批与普通查询 API 不变。

## T8 — Observability、Audit 与 Evidence Trace

**Goal:** 建立 request → analysis → tool → evidence → conclusion 的可追溯链路。

**修改范围:**

- 新增 `backend/wms_agent/apps/warehouse/ports/analysis_observability.py`
- 新增 Integration logging/tracing Adapter
- 扩展 Agent event 类型与 ToolExecutionTracker 使用点
- MCP Server structured logging

**Dependencies:** T2、T4、T5、T6。

**Acceptance Criteria:**

- start/end、tool、retry、conflict、assembly 事件含必需关联键；
- duration、status、errorCode 可查询；
- authorization、完整 Prompt、敏感引用不记录；
- 不新增 Agent/MCP 直连业务数据库；
- PARTIAL 和冲突可定位到 Evidence ID。

**Test / Evaluation Requirements:**

- Unit Test：并行 request/analysis 不串线、duration、ID 关联；
- Log capture Test：敏感字段脱敏；
- Integration Test：从 Result evidenceId 回溯 Tool event；
- Architecture Test：Observability 通过 Port/Adapter。

## T9 — Intent、Agent 与 Critical Evaluation

**Goal:** 建立符合 AGENTS.md Definition of Done 的可重复 Evaluation 套件。

**修改范围:**

- 新增 `backend/evals/` runner 与 case files；仓库当前不存在 Evaluation harness，因此采用最小 pytest 可执行入口。

**Dependencies:** T6、T7、T8。

**Acceptance Criteria:**

- Intent cases 区分 AVAILABLE_STOCK_LOW、普通库存查询、范围外异常和写请求；
- Agent cases 覆盖三类 Evidence、SUCCESS/PARTIAL/FAILED、NO_DATA、冲突、权限、timeout；
- Critical cases 验证无 Evidence 不确认根因、无数值置信度、无写 Tool、无权限泄漏；
- Evaluation 输出机器可读报告和失败 case ID。

**Test / Evaluation Requirements:**

- Intent Evaluation PASS；
- Agent Evaluation PASS；
- Critical Evaluation Cases PASS；
- 固定随机性或使用可重复 Fake Model 进行 CI，真实模型评测作为独立环境验证。

## T10 — End-to-End、Architecture Verification 与 G2 证据

**Goal:** 完成全链路验证并生成可审计的 VERIFY Artifact。

**修改范围:**

- 新增端到端 Integration Test；
- 扩展 `backend/tests/test_architecture.py`；
- 新增 `deliveries/D-001-inventory-analysis-enhance/verification.md`。

**Dependencies:** T1–T9。

**Acceptance Criteria:**

- Main Graph → SubAgent → MCP Client → MCP Server → Fake/Real Contract WMS 全链路通过；
- 三个 Tool 之外的调用被拒绝；
- MCP 无数据库依赖、apps 无 Integration 反向依赖；
- requirement Acceptance Criteria 与 behaviors B1–B21 均有测试/Evaluation 证据；
- 无未批准 Scope Change；
- Java WMS Provider Contract 证据已附。

**Test / Evaluation Requirements:**

- Backend Unit Test PASS；
- Integration Test PASS；
- MCP Contract Test PASS；
- Intent Evaluation PASS；
- Agent Evaluation PASS；
- Critical Evaluation Cases PASS；
- Architecture Rule PASS。

## Task DAG

```text
T1 State/Context ─────┬──────────────> T5 MCP Adapter ──> T6 SubAgent ──> T7 API
                      │                    ▲                 │              │
                      └─> T2 Models ───────┘                 ├─> T8 Trace ──┤
                              ▲                              │              │
T3 Java WMS ──> T4 MCP Server┴──────────────────────────────┘              │
                                                                            v
                                                               T9 Evaluations
                                                                            │
                                                                            v
                                                               T10 E2E / G2
```

推荐执行顺序：`T1 → T2 → T3/T4 → T5 → T6 → T7/T8 → T9 → T10`。T3 位于外部 Java WMS Repository，可与 T1/T2 并行；T4 可先使用严格 Mock Contract，但 T10 必须取得真实 Provider Contract 证据。

## Behavior Coverage

| Behaviors | Tasks |
|---|---|
| B1–B5 | T1、T7、T9 |
| B6–B7 | T4、T5、T6、T10 |
| B8–B13 | T2、T3、T6、T9 |
| B14–B16 | T2、T4、T6、T9 |
| B17–B18 | T2、T7、T9 |
| B19–B21 | T3、T5、T6、T9、T10 |

## G1 Checklist

- [ ] decisions.md 与已批准 requirement/behaviors 一致。
- [ ] contracts.md 未引入第四类 Evidence、第三类原因或新异常。
- [ ] Java WMS 外部 Provider Contract 的负责人和交付方式已确认。
- [ ] Request/Session Context 的安全来源与 MCP 元数据传递方式可实现。
- [ ] 三个 READ Tool 白名单已确认。
- [ ] tasks.md 覆盖全部 Definition of Done。
- [ ] 当前没有业务代码、测试代码或 Evaluation 代码改动。

