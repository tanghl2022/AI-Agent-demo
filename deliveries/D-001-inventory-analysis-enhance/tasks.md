# 库存异常原因分析增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于只读 MCP Evidence、能够区分事实与原因确定性的库存异常原因分析闭环。

**Architecture:** 复用现有 `INVENTORY_ANALYSIS` 与 `InventoryAnalysisSubAgent`。固定查询继续使用 Capability；SubAgent 的动态查询改为通过 `InventoryEvidencePort -> MCP Adapter -> MCP Server -> Java WMS API`，所有 Tool 返回统一 Evidence Envelope，确定性原因只由 Java WMS assessment 提供。

**Tech Stack:** Python 3、LangGraph、LangChain Tool Calling、MCP Python SDK、httpx、Pydantic 2、pytest；外部 Java WMS REST API。

**Spec:** `deliveries/D-001-inventory-analysis-enhance/requirement.md`、`behaviors.md`、`decisions.md`、`contracts.md`

## Global Constraints

- 只有 G1 APPROVED 后才能开始 IMPLEMENT。
- 不得修改已批准的 requirement、behaviors 或 architecture decisions；超出 Scope 必须停止并报告。
- Agent、MCP、LLM 不得访问数据库或实现确定性库存业务规则。
- InventoryAnalysisSubAgent 只能获得四个已批准的只读 Tool。
- 所有代码注释使用中文，并保持现有代码风格。
- 每个业务代码改动先写失败测试，再做最小实现。
- 修改 MCP Tool 必须增加 Contract Test；修改 Agent 必须运行 Agent Evaluation；修改 Intent 行为必须运行 Intent Evaluation。

## Review Focus

1. `user_message` 在主图中未丢失，SubAgent 不会收到空问题——由 T5 节点测试覆盖。
2. 404 无数据与 timeout/5xx 技术失败严格区分——由 T2、T3 Contract Test 覆盖。
3. 部分 Tool 失败时不得使用失败维度确认或排除原因——由 T6 SubAgent 测试覆盖。
4. 受信任身份上下文不进入 LLM Tool 参数且完整转发——由 T3、T4 安全测试覆盖。
5. Tool Registry 无法注入写 Tool——由 T4 装配测试与 T8 Critical Evaluation 覆盖。

---

## File Structure

### Backend 新增

- `backend/wms_agent/apps/warehouse/models/evidence.py`：Evidence 与分析结果业务模型。
- `backend/wms_agent/apps/warehouse/ports/inventory_evidence.py`：应用层 MCP Evidence Port。
- `backend/wms_agent/integrations/mcp/inventory_evidence_client.py`：MCP Client Adapter。
- `backend/wms_agent/integrations/mcp/container.py`：MCP 连接生命周期与 Adapter 装配。
- `backend/tests/test_inventory_evidence_models.py`：模型约束测试。
- `backend/tests/test_mcp_inventory_adapter.py`：MCP Adapter 与身份上下文测试。
- `backend/tests/test_inventory_analysis_node.py`：问题传递与状态写回测试。
- `backend/tests/test_inventory_analysis_subagent.py`：证据化推理行为测试。
- `backend/evals/inventory_analysis_cases.yaml`：Agent Evaluation 用例。
- `backend/evals/inventory_intent_cases.yaml`：Intent Evaluation 用例。

### Backend 修改

- `backend/wms_agent/apps/warehouse/agent/state/agent_state.py`：增加分析状态和 Evidence ID。
- `backend/wms_agent/apps/warehouse/agent/nodes/agent/inventory_analysis.py`：使用 `user_message` 并写回结构化结果。
- `backend/wms_agent/apps/warehouse/agent/nodes/agent/parameter_validation.py`：分析请求要求 `material_code`。
- `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/agent.py`：返回结构化结果并消费 Evidence。
- `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/prompt.py`：落实事实/确认/候选/未知表达规则。
- `backend/wms_agent/apps/warehouse/agent/container.py`：只向 SubAgent 注入 MCP 只读 Tool。
- `backend/wms_agent/apps/warehouse/container.py`、`backend/wms_agent/bootstrap.py`：注入 MCP Adapter 生命周期。
- `backend/wms_agent/config.py`、`backend/.env.example`：增加 MCP 配置。
- `backend/tests/test_parameter_validation_node.py`、`backend/tests/test_intent_recognition_node.py`、`backend/tests/test_architecture.py`：补充回归和架构规则。

### MCP Server 新增或修改

- `mcp-server/wms_mcp/models/evidence.py`：MCP Evidence schema。
- `mcp-server/wms_mcp/clients/wms_client.py`：真实 Java WMS 只读 Client、重试和熔断。
- `mcp-server/wms_mcp/tools/inventory.py`：四个只读 Tool 与统一错误映射。
- `mcp-server/wms_mcp/server.py`：注册 Tool，保留 deprecated `get_stock` 兼容入口但不供 SubAgent 使用。
- `mcp-server/wms_mcp/config.py`、`mcp-server/.env.example`：WMS URL、timeout、retry、circuit breaker 配置。
- `mcp-server/tests/test_inventory_contract.py`：Tool schema 与行为 Contract Test。
- `mcp-server/tests/test_wms_client.py`：HTTP 映射、重试、熔断和身份透传测试。

### 外部依赖

- Java WMS 仓库：实现 `contracts.md` 第 5 节四个只读 API 及确定性 assessment；该仓库不在当前工作区，必须由其负责人提供通过的契约验证结果。

---

### Task 1: 建立 Evidence 与分析结果模型

**Files:**
- Create: `backend/wms_agent/apps/warehouse/models/evidence.py`
- Create: `backend/tests/test_inventory_evidence_models.py`

**Interfaces:**
- Produces: `EvidenceStatus`、`EvidenceErrorCode`、`CauseCertainty`、`EvidenceEnvelope`、`CauseConclusion`、`InventoryAnalysisStatus`、`InventoryAnalysisResult`。
- Consumes: `contracts.md` 第 3、4、8 节。

- [ ] **Step 1:** 编写模型失败测试，覆盖合法 Envelope、未知枚举拒绝、失败状态必须包含 error、成功状态不得包含 error、Evidence ID 去重和分析结果序列化。
- [ ] **Step 2:** 运行 `pytest backend/tests/test_inventory_evidence_models.py -v`，确认因模型不存在而失败。
- [ ] **Step 3:** 在 `evidence.py` 实现上述 Pydantic 模型与跨字段校验，不包含业务原因计算。
- [ ] **Step 4:** 再次运行同一测试，预期全部 PASS。
- [ ] **Step 5:** 运行 `pytest backend/tests/test_agent_state.py -v`，确认现有状态模型未回归。

**Depends:** 无。

### Task 2: 固化 Java WMS Provider Contract

**Files:**
- External: Java WMS 对应 Controller、Service、DTO 和 Unit Test。
- Test: Java WMS Contract Test（路径由 Java 仓库约定）。

**Interfaces:**
- Produces: `contracts.md` 第 5 节四个 GET API。
- Consumes: 受信任请求头和 Java WMS 现有权限上下文。

- [ ] **Step 1:** 为 inventory detail、reservation、freeze、location API 编写 Provider Contract Test，覆盖 200、404、401/403、非法参数和 assessments schema。
- [ ] **Step 2:** 运行 Java WMS Contract Test，确认新增契约在实现前失败。
- [ ] **Step 3:** 在 Java WMS Service 实现查询与确定性 assessment；不得把规则放到 Controller 或 MCP。
- [ ] **Step 4:** 运行 Java Unit Test 与 Contract Test，预期全部 PASS。
- [ ] **Step 5:** 输出可供当前仓库消费的契约版本或构建标识，并附 G1/G2 证据。

**Depends:** T1 的枚举语义；当前仓库可用 Mock Server 并行开发，但 Integration PASS 依赖本任务。

### Task 3: 实现 MCP WMS Client 与 Evidence Tool

**Files:**
- Create: `mcp-server/wms_mcp/models/evidence.py`
- Modify: `mcp-server/wms_mcp/clients/wms_client.py`
- Modify: `mcp-server/wms_mcp/tools/inventory.py`
- Modify: `mcp-server/wms_mcp/server.py`
- Create: `mcp-server/wms_mcp/config.py`
- Modify: `mcp-server/.env.example`
- Create: `mcp-server/tests/test_wms_client.py`
- Create: `mcp-server/tests/test_inventory_contract.py`

**Interfaces:**
- Produces: MCP tools `inventory_detail_query`、`inventory_reservation_query`、`inventory_freeze_query`、`location_query`。
- Consumes: T2 Java WMS API 和 `contracts.md` Evidence Envelope。

- [ ] **Step 1:** 编写 WMS Client 失败测试，覆盖 URL 编码、五个身份头、10 秒默认 timeout、一次受控重试、不可重试状态和连续 5 次失败后熔断 30 秒。
- [ ] **Step 2:** 编写 Tool Contract 失败测试，覆盖四个 Tool 的输入 schema、Envelope 字段、200/404/403/timeout/非法响应映射以及敏感错误脱敏。
- [ ] **Step 3:** 运行 `pytest mcp-server/tests/test_wms_client.py mcp-server/tests/test_inventory_contract.py -v`，确认实现前失败。
- [ ] **Step 4:** 实现配置、Pydantic schema、异步 WMS Client、重试与熔断；只调用 Java WMS API，不访问数据库。
- [ ] **Step 5:** 实现四个 Tool 和统一映射，在 `server.py` 注册；旧 `get_stock` 标记 deprecated。
- [ ] **Step 6:** 重跑两组测试，预期全部 PASS。
- [ ] **Step 7:** 运行 `pytest mcp-server/tests -v`，确认 MCP 回归测试全部 PASS。

**Depends:** T2 契约；可使用严格 MockTransport 先行完成。

### Task 4: 建立 Backend MCP Port、Adapter 与安全装配

**Files:**
- Create: `backend/wms_agent/apps/warehouse/ports/inventory_evidence.py`
- Create: `backend/wms_agent/integrations/mcp/__init__.py`
- Create: `backend/wms_agent/integrations/mcp/inventory_evidence_client.py`
- Create: `backend/wms_agent/integrations/mcp/container.py`
- Modify: `backend/wms_agent/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/wms_agent/bootstrap.py`
- Modify: `backend/wms_agent/apps/warehouse/container.py`
- Modify: `backend/wms_agent/apps/warehouse/agent/container.py`
- Create: `backend/tests/test_mcp_inventory_adapter.py`
- Modify: `backend/tests/test_architecture.py`

**Interfaces:**
- Produces: `InventoryEvidencePort` 四个异步方法与对应 LangChain 只读 Tool。
- Consumes: T1 模型、T3 MCP Tools、受信任 Request Context。

- [ ] **Step 1:** 编写 Port/Adapter 失败测试，验证方法签名、snake_case/camelCase 映射、Envelope 解析、身份上下文不出现在 LLM 参数中、缺少上下文时 fail closed。
- [ ] **Step 2:** 编写装配失败测试，验证 Tool 名称集合必须精确等于四个白名单 Tool，注入写 Tool 或未知 Tool 时启动失败。
- [ ] **Step 3:** 扩展 Architecture Test，禁止 `apps/` 直接依赖具体 MCP SDK或 `integrations.mcp`。
- [ ] **Step 4:** 运行相关测试，确认实现前失败。
- [ ] **Step 5:** 实现 Port、Adapter、配置、生命周期与组合根注入；应用层只依赖 Port。
- [ ] **Step 6:** 重跑相关测试，预期全部 PASS。
- [ ] **Step 7:** 运行 `pytest backend/tests/test_resource_lifecycle.py backend/tests/test_architecture.py -v`，确认生命周期和边界无回归。

**Depends:** T1、T3。

### Task 5: 修复分析请求上下文与参数校验

**Files:**
- Modify: `backend/wms_agent/apps/warehouse/agent/state/agent_state.py`
- Modify: `backend/wms_agent/apps/warehouse/agent/nodes/agent/inventory_analysis.py`
- Modify: `backend/wms_agent/apps/warehouse/agent/nodes/agent/parameter_validation.py`
- Create: `backend/tests/test_inventory_analysis_node.py`
- Modify: `backend/tests/test_parameter_validation_node.py`

**Interfaces:**
- Produces: Node 输入 `user_message`；输出 `answer`、`analysis_status`、`analysis_evidence_ids`。
- Consumes: T1 `InventoryAnalysisResult`。

- [ ] **Step 1:** 编写失败测试，证明 Node 将完整 `user_message` 传给 SubAgent，并拒绝空问题替代；验证结构化结果写回 State。
- [ ] **Step 2:** 编写参数校验失败测试，验证 `INVENTORY_ANALYSIS` 缺少 `material_code` 时进入 `CLARIFICATION_REQUIRED`，存在物料时继续。
- [ ] **Step 3:** 运行两组测试，确认当前实现失败。
- [ ] **Step 4:** 最小修改 Node、AgentState 和参数校验，统一使用 `user_message`。
- [ ] **Step 5:** 重跑测试，预期全部 PASS。
- [ ] **Step 6:** 运行 `pytest backend/tests/test_agent_state.py backend/tests/test_parameter_validation_node.py -v`，确认回归通过。

**Depends:** T1。

### Task 6: 增强 InventoryAnalysisSubAgent 的证据化分析

**Files:**
- Modify: `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/agent.py`
- Modify: `backend/wms_agent/apps/warehouse/subagents/inventory_analysis/prompt.py`
- Modify: `backend/wms_agent/apps/warehouse/agent/container.py`
- Create: `backend/tests/test_inventory_analysis_subagent.py`

**Interfaces:**
- Produces: `ainvoke(question: str) -> InventoryAnalysisResult`。
- Consumes: T1 模型和 T4 四个只读 Tool。

- [ ] **Step 1:** 编写失败测试，覆盖四个 Tool 按需选择、`CONFIRMED` 原样保留、仅相关事实降级为 `POSSIBLE`、证据不足、证据冲突、多原因顺序、NO_DATA、PARTIAL、全部失败和 8 轮终止。
- [ ] **Step 2:** 编写安全失败测试，验证未知 Tool 不执行、写 Tool 不可见、失败 Evidence 不用于排除原因、回答包含 Evidence ID 与固定段落。
- [ ] **Step 3:** 运行 `pytest backend/tests/test_inventory_analysis_subagent.py -v`，确认当前实现失败。
- [ ] **Step 4:** 更新 Prompt 和 Tool loop，使 ToolMessage 使用规范 JSON 而非 Python `str(dict)`，并返回结构化结果。
- [ ] **Step 5:** 实现确定性的结果汇总保护：状态聚合、Evidence ID 收集和 WMS assessment 保真；不实现业务原因规则。
- [ ] **Step 6:** 重跑测试，预期全部 PASS。

**Depends:** T1、T4、T5。

### Task 7: 完成意图与主流程集成测试

**Files:**
- Modify: `backend/tests/test_intent_recognition_node.py`
- Modify: `backend/tests/test_modular_runtime.py`
- Create: `backend/tests/test_inventory_analysis_integration.py`

**Interfaces:**
- Produces: 主流程从用户请求到 Evidence 化回答的集成保障。
- Consumes: T3 至 T6。

- [ ] **Step 1:** 增加意图测试：原因/为什么/综合分析进入 `INVENTORY_ANALYSIS`，单一库存和库位查询保持原路由。
- [ ] **Step 2:** 增加端到端失败测试：Main Graph → SubAgent → MCP fake server → Fake Java WMS，验证 requestId、身份上下文、Evidence ID 和最终 answer。
- [ ] **Step 3:** 增加 403、404、部分失败和非法响应集成测试。
- [ ] **Step 4:** 运行新增测试，确认实现或装配缺失时失败。
- [ ] **Step 5:** 完成必要的组合根修正，不改变已批准契约。
- [ ] **Step 6:** 重跑新增测试和 `pytest backend/tests -v`，预期全部 PASS。

**Depends:** T3、T4、T5、T6。

### Task 8: 建立 Intent Evaluation 与 Agent Evaluation

**Files:**
- Create: `backend/evals/inventory_intent_cases.yaml`
- Create: `backend/evals/inventory_analysis_cases.yaml`
- Modify/Create: 仓库既有 Evaluation runner 对应文件；若当前不存在 runner，先在 G1 记录并采用最小 pytest 驱动 runner。

**Interfaces:**
- Produces: 可重复执行的 Intent、Agent 和 Critical Evaluation 报告。
- Consumes: behaviors B1-B20。

- [ ] **Step 1:** 建立 Intent cases，至少覆盖原因分析、模糊异常补问、单一查询、写操作请求和未知请求。
- [ ] **Step 2:** 建立 Agent cases，覆盖 confirmed、possible、unknown、conflict、partial、failed、forbidden、no-data、多原因和 8 轮上限。
- [ ] **Step 3:** 建立 Critical cases，验证无 Evidence 不下确定性结论、失败不等于无数据、禁止写 Tool、租户/仓库隔离和敏感信息不泄露。
- [ ] **Step 4:** 运行 Evaluation，记录基线失败项。
- [ ] **Step 5:** 仅调整 Prompt/测试数据映射以满足已批准行为，不新增业务规则。
- [ ] **Step 6:** 重跑 Intent Evaluation、Agent Evaluation 和 Critical Evaluation，预期全部 PASS。

**Depends:** T6、T7。

### Task 9: 完成 VERIFY 证据与 G2 输入

**Files:**
- Create: `deliveries/D-001-inventory-analysis-enhance/verification.md`
- Modify: `deliveries/D-001-inventory-analysis-enhance/tasks.md`，仅勾选实际完成项，不改变任务语义。

**Interfaces:**
- Produces: Definition of Done 的可审计验证记录。
- Consumes: T1-T8 的测试与 Evaluation 输出。

- [ ] **Step 1:** 运行 Backend Unit/Integration Test 全集并记录命令、时间和结果。
- [ ] **Step 2:** 运行 MCP Contract Test 全集并记录结果。
- [ ] **Step 3:** 收集 Java WMS Unit/Contract Test 的外部构建证据。
- [ ] **Step 4:** 运行 Intent、Agent、Critical Evaluation 并记录结果。
- [ ] **Step 5:** 运行 Architecture Rule 检查并确认无边界违规。
- [ ] **Step 6:** 对照 requirement Acceptance Criteria 与 behaviors B1-B20 逐项建立证据映射。
- [ ] **Step 7:** 确认无未批准 Scope Change、无写 Tool 暴露、无未解决高风险问题后，提交 G2 Review。

**Depends:** T1-T8 全部完成。

## Task Dependency Order

```text
T1 ─┬─> T4 ─┬─> T6 ─> T7 ─> T8 ─> T9
    │       └─> T5 ─┘
T2 ─> T3 ────> T4
```

T2 的 Java WMS 仓库不在当前工作区，可与 T1 并行；T3 可先基于严格 Mock Contract 开发，但 T7 Integration PASS 与 T9 完成必须取得 T2 的真实 Provider Contract 证据。

## Behavior Coverage Matrix

| Behavior | Owning Tasks |
|---|---|
| B1 识别原因分析请求 | T7、T8 |
| B2 单一事实查询不升级 | T7、T8 |
| B3 完整传递用户问题 | T5、T7 |
| B4 缺少必要调查范围 | T5、T8 |
| B5 动态收集相关证据 | T4、T6、T8 |
| B6 充分证据确认原因 | T2、T3、T6、T8 |
| B7 相关现象不确认因果 | T6、T8 |
| B8 多个原因同时成立 | T2、T6、T8 |
| B9 未发现可确认原因 | T6、T8 |
| B10 证据缺失 | T3、T6、T8 |
| B11 证据冲突 | T6、T8 |
| B12 部分 Tool 失败 | T3、T6、T7、T8 |
| B13 必要 Tool 全部失败 | T3、T6、T8 |
| B14 成功但无业务数据 | T2、T3、T6、T8 |
| B15 无访问权限 | T2、T3、T4、T7、T8 |
| B16 超过 Tool Calling 上限 | T6、T8 |
| B17 分析全程只读 | T4、T6、T8 |
| B18 区分事实、结论、推断和未知 | T1、T6、T8 |
| B19 结论可追溯 | T1、T3、T6、T7 |
| B20 只提出未执行建议 | T6、T8 |

## G1 Review Checklist

- [ ] requirement.md 与 behaviors.md 已标记 DEFINE APPROVED，且未被设计阶段擅自改写业务含义。
- [ ] decisions.md 不违反 AGENTS.md、architecture.md 和 Accepted ADR。
- [ ] contracts.md 明确 Tool、API、Evidence、错误、安全和兼容契约。
- [ ] tasks.md 覆盖 Unit、Integration、MCP Contract、Intent Evaluation、Agent Evaluation、Critical Evaluation 和 Architecture Rule。
- [ ] Java WMS 外部依赖、负责人和契约验证方式已确认。
- [ ] 第一阶段四个只读 Tool 范围已确认。
- [ ] 没有业务代码修改，没有提前进入 IMPLEMENT。

