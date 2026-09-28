# D-001 库存异常原因分析增强 Contracts

## Status

- 阶段：DESIGN
- 版本：V1
- 状态：G1 APPROVED（含已批准的 Error Trace ID Contract Clarification）
- 本文只定义逻辑 Contract，不代表代码已经实现

## 1. Naming and Serialization

- 边界 JSON 使用 `camelCase`；Python 内部可使用 `snake_case`。
- 时间使用带时区的 RFC 3339。
- 数量使用非负整数；具体计量单位由 Java WMS 返回。
- 所有 enum 遇到未知值必须验证失败，不得静默降级。

## 2. Inventory Analysis Request Contract

```json
{
  "analysisType": "AVAILABLE_STOCK_LOW",
  "materialCode": "MAT001",
  "userMessage": "为什么 MAT001 的可用库存这么低？",
  "requestContext": {
    "requestId": "req-001",
    "conversationId": "conv-001",
    "userId": "U001",
    "tenantId": "T001",
    "warehouseId": "WH001"
  }
}
```

### Validation

- `analysisType` 必须等于 `AVAILABLE_STOCK_LOW`。
- `materialCode` trim 后长度为 1–64。
- `userMessage` 必须是当前轮非空原始消息。
- `requestId`、`conversationId`、`userId`、`tenantId` 必填。
- `warehouseId` 必须来自受信任 Session 或经用户选择后通过权限验证。
- `authorization` 作为传输秘密单独携带，不属于可持久化 Request JSON。
- 任一身份字段不得从 LLM 输出或 Tool 参数取得。

## 3. Analysis Result Contract

```json
{
  "analysisId": "ana-001",
  "status": "PARTIAL",
  "subject": {
    "analysisType": "AVAILABLE_STOCK_LOW",
    "materialCode": "MAT001",
    "tenantId": "T001",
    "warehouseId": "WH001"
  },
  "facts": [],
  "possibleCauses": [],
  "unknowns": [],
  "evidences": [],
  "limitations": [],
  "successfulScopes": ["INVENTORY_SUMMARY", "RESERVATION"],
  "failedScopes": ["FREEZE"],
  "answer": "自然语言解释",
  "startedAt": "2026-09-28T10:00:00+08:00",
  "completedAt": "2026-09-28T10:00:02+08:00"
}
```

### Analysis Status

| Status | Meaning |
|---|---|
| `SUCCESS` | 三个 Evidence Scope 均完成；完成包括 SUCCESS 或明确 NO_DATA |
| `PARTIAL` | 至少一个 Scope 完成，至少一个 Scope FAILED；或存在 Evidence Conflict |
| `FAILED` | 无可用 Evidence、权限失败，或可信上下文无法建立 |

状态只描述分析执行完整性，不代表原因已确认。

### Subject

`subject` 固定包含 `analysisType`、`materialCode`、`tenantId`、`warehouseId`。不得包含 authorization。

### Failure before Evidence Collection

Request Context 尚未成功建立、尚未进入 Evidence Collection 时，允许返回以下失败形态；不得为补齐正常分析结果而猜测 subject 身份字段或伪造 Evidence：

```json
{
  "status": "FAILED",
  "evidences": [],
  "error": {
    "code": "CONTEXT_REQUIRED",
    "traceId": "trace-xxx"
  }
}
```

此形态优先于正常分析结果的必填字段要求，不产生 FACT 或 POSSIBLE_CAUSE。Result 的 `error` 承载第 11 节诊断错误；上述最小失败形态允许只含 `code` 和 `traceId`。

## 4. Classified Item Contract

### Fact

```json
{
  "classification": "FACT",
  "code": "AVAILABLE_QTY",
  "statement": "可用库存为 20",
  "value": 20,
  "unit": "EA",
  "evidenceIds": ["ev-summary-001"]
}
```

### Possible Cause

```json
{
  "classification": "POSSIBLE_CAUSE",
  "code": "RESERVED_STOCK_HIGH",
  "statement": "预占库存可能影响当前可用库存",
  "evidenceIds": ["ev-reservation-001"]
}
```

`code` 只允许 `RESERVED_STOCK_HIGH`、`FROZEN_STOCK_HIGH`。

### Unknown

```json
{
  "classification": "UNKNOWN",
  "code": "FREEZE_EVIDENCE_UNAVAILABLE",
  "statement": "冻结证据查询失败，无法判断冻结库存影响",
  "evidenceIds": ["ev-freeze-001"]
}
```

- `evidenceId` 与 `errorTraceId` 是不同语义的标识，不得混用。`evidenceId` 标识完成 Evidence Collection 后产生的业务证据；所有分类项中的业务 Evidence 引用必须存在于同一 `Result.evidences`。
- `facts`、`possibleCauses` 的每个分类项必须有非空 `evidenceIds`；`unknowns` 的 `evidenceIds` 可省略，存在时按第 14 节校验。
- `errorTraceId` 标识请求、上下文建立、权限检查、MCP/Java WMS 调用或其他技术失败的诊断 Trace。Result 错误使用 `error.traceId` 承载；该标识不属于业务 Evidence，不填入 `evidenceIds`。
- 上下文建立前、Evidence Collection 开始前失败采用第 3 节失败形态。Error Trace 仅用于日志、Trace、排障和错误关联，绝不能作为支持 FACT 或 POSSIBLE_CAUSE 的证据。

## 5. Common Evidence Contract

```json
{
  "evidenceId": "ev-summary-001",
  "analysisId": "ana-001",
  "toolCallId": "tool-001",
  "evidenceType": "InventorySummaryEvidence",
  "collectionStatus": "SUCCESS",
  "source": "JAVA_WMS",
  "materialCode": "MAT001",
  "tenantId": "T001",
  "warehouseId": "WH001",
  "inventoryVersion": "v-1001",
  "observedAt": "2026-09-28T10:00:01+08:00",
  "data": {},
  "error": null
}
```

### Evidence Collection Status

- `SUCCESS`
- `NO_DATA`
- `FAILED`
- `FORBIDDEN`

`SUCCESS` 必须有 data 且 error 为 null。`NO_DATA`、`FAILED`、`FORBIDDEN` 必须有 error；`FAILED/FORBIDDEN` 的 data 必须为 null。`NO_DATA` 可包含空集合型 data，但不能伪装为查询失败。

## 6. InventorySummaryEvidence

```json
{
  "materialCode": "MAT001",
  "totalQty": 100,
  "availableQty": 20,
  "reservedQty": 70,
  "frozenQty": 10,
  "unit": "EA",
  "anomalyAssessment": {
    "code": "AVAILABLE_STOCK_LOW",
    "determination": "MATCHED",
    "ruleVersion": "available-stock-v1"
  }
}
```

`determination`：`MATCHED | NOT_MATCHED | UNKNOWN`。MCP 和 Agent 不得重算任何数量或 assessment。

## 7. ReservationEvidence

```json
{
  "materialCode": "MAT001",
  "totalReservedQty": 70,
  "unit": "EA",
  "reservationCount": 2,
  "records": [
    {
      "reservationRef": "R-001",
      "quantity": 40,
      "status": "WMS_DEFINED_STATUS",
      "businessType": "WMS_DEFINED_TYPE",
      "createdAt": "2026-09-28T09:00:00+08:00"
    }
  ],
  "candidateAssessment": {
    "code": "RESERVED_STOCK_HIGH",
    "condition": "MATCHED",
    "causeDetermination": "NOT_CONFIRMED",
    "ruleVersion": "reservation-v1"
  }
}
```

`condition`：`MATCHED | NOT_MATCHED | UNKNOWN`。

`causeDetermination`：`CONFIRMED | NOT_CONFIRMED | UNKNOWN`。若为 `NOT_CONFIRMED` 且 condition 为 `MATCHED`，结果可产生 `POSSIBLE_CAUSE`；若为 `CONFIRMED`，确定性判断作为 `FACT`，不得扩展批准的三类输出分类。

## 8. FreezeEvidence

```json
{
  "materialCode": "MAT001",
  "totalFrozenQty": 10,
  "unit": "EA",
  "freezeCount": 1,
  "records": [
    {
      "freezeRef": "F-001",
      "quantity": 10,
      "status": "WMS_DEFINED_STATUS",
      "reasonCode": "WMS_DEFINED_REASON",
      "reasonText": "允许当前用户查看的冻结原因",
      "createdAt": "2026-09-28T09:30:00+08:00"
    }
  ],
  "candidateAssessment": {
    "code": "FROZEN_STOCK_HIGH",
    "condition": "MATCHED",
    "causeDetermination": "NOT_CONFIRMED",
    "ruleVersion": "freeze-v1"
  }
}
```

condition 与 causeDetermination 的映射规则与 ReservationEvidence 相同。

## 9. MCP Tool Contracts

三个 Tool 的 LLM 可见输入一致：

```json
{
  "material_code": "MAT001"
}
```

| Tool | Output Evidence | Java WMS Logical API |
|---|---|---|
| `get_inventory_summary_evidence` | `InventorySummaryEvidence` | `GET /api/wms/inventory/{materialCode}/summary-evidence` |
| `get_reservation_evidence` | `ReservationEvidence` | `GET /api/wms/inventory/{materialCode}/reservation-evidence` |
| `get_freeze_evidence` | `FreezeEvidence` | `GET /api/wms/inventory/{materialCode}/freeze-evidence` |

### Trusted Transport Metadata

MCP Client 必须附加但不得暴露给 LLM：`authorization`、`requestId`、`analysisId`、`userId`、`tenantId`、`warehouseId`、`conversationId`。

### Tool Output

Tool 必须返回第 5 节 Common Evidence Contract，data 为对应 Evidence 类型。禁止返回自由格式字符串或 Python `str(dict)`。

## 10. Java WMS API Rules

- API 只读，使用 GET；
- 每个请求执行 Authentication、Authorization、Tenant Validation、Warehouse Validation；
- Java WMS 返回 `inventoryVersion`、`observedAt`、业务单位和确定性 assessment；
- Java WMS 不返回调用者无权查看的业务引用或原因文本；
- Java WMS 负责所有“LOW/HIGH”规则及 ruleVersion；
- MCP 不得连接 Java WMS 数据库。

## 11. Error Contract

```json
{
  "code": "UPSTREAM_TIMEOUT",
  "message": "库存服务查询超时",
  "retryable": true,
  "traceId": "trace-001"
}
```

允许的 code：

- `INVALID_ARGUMENT`
- `CONTEXT_REQUIRED`
- `NOT_FOUND`
- `FORBIDDEN`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `UPSTREAM_INVALID_RESPONSE`
- `CIRCUIT_OPEN`
- `TOOL_ITERATION_LIMIT`
- `ANALYSIS_DEADLINE_EXCEEDED`
- `EVIDENCE_CONFLICT`
- `INTERNAL_ERROR`

错误 message 必须安全、可理解，不包含 Token、堆栈、数据库结构或未脱敏敏感信息。

## 12. HTTP / Transport Mapping

| Condition | Evidence Status | Error Code | Retry |
|---|---|---|---:|
| 2xx + valid payload | `SUCCESS` | null | 否 |
| 404 / explicit empty | `NO_DATA` | `NOT_FOUND` | 否 |
| 400 / 422 | `FAILED` | `INVALID_ARGUMENT` | 否 |
| 401 / 403 | `FORBIDDEN` | `FORBIDDEN` | 否 |
| timeout | `FAILED` | `UPSTREAM_TIMEOUT` | 1 次 |
| connect / 502 / 503 / 504 | `FAILED` | `UPSTREAM_UNAVAILABLE` | 1 次 |
| other 5xx | `FAILED` | `UPSTREAM_UNAVAILABLE` | 否 |
| invalid 2xx schema | `FAILED` | `UPSTREAM_INVALID_RESPONSE` | 否 |
| circuit open | `FAILED` | `CIRCUIT_OPEN` | 否 |

## 13. Evidence Conflict Contract

```json
{
  "code": "EVIDENCE_CONFLICT",
  "kind": "VALUE_CONFLICT",
  "field": "reservedQty",
  "evidenceIds": ["ev-summary-001", "ev-reservation-001"],
  "message": "相同库存版本的预占数量不一致"
}
```

`kind`：`VALUE_CONFLICT | TEMPORAL_CONFLICT`。冲突项必须进入 unknowns 和 limitations；相关 Evidence 均保留，不覆盖原值。

## 14. Evidence-to-Conclusion References

- `facts[*].evidenceIds`、`possibleCauses[*].evidenceIds` 必须非空；`unknowns[*].evidenceIds` 如果存在，也属于业务 Evidence 引用；
- 上述数组中的每个引用必须存在于同一 `Result.evidences[*].evidenceId`；
- 不允许跨 analysisId 引用；
- Result Assembler 必须拒绝 dangling business Evidence reference；`error.traceId` / `errorTraceId` 不参与 Evidence Referential Integrity 校验，也不得混入业务 Evidence 引用；
- 同一 Evidence 可被多个分类项引用；
- Evidence 本身不可引用分类项，保持单向关系。

第 4 节的 Error Trace 例外优先：尚未进入 Evidence Collection 的失败可有空 evidences 和独立 error.traceId，无需为诊断 Trace 创建业务 Evidence。

## 15. Natural-language Answer Contract

`InventoryAnalysisAnswerRenderer` 的逻辑接口为 `render(result: InventoryAnalysisResult) -> answer: str`；此处只约定输入输出，不限定同步或异步实现。唯一内容来源为确定性 Assembler 生成的 Result；Result 中的 `answer` 是派生输出，不作为渲染输入或事实来源。Renderer 只读结构化字段，调用方仅回填返回的 answer。

实现与使用场景：

- `DeterministicAnswerRenderer`：确定性模板，用于测试、CI 和降级；同一 Result 产生相同 answer。
- `LlmAnswerRenderer`：生产环境可选，只允许基于同一 Result 调整措辞和句子组织，不允许新增 Fact、Cause、Classification、Unknown 或改变任何结构化结论。

两种实现均按以下顺序覆盖内容：

1. 调查对象与 status；
2. `FACT`；
3. `POSSIBLE_CAUSE`；
4. `UNKNOWN`；
5. `limitations`；
6. 未执行建议（仅在存在时）。

answer 不显示 LLM 数值置信度，不将 `POSSIBLE_CAUSE` 称为“已确认根因”，不得包含结构化 Result 中不存在的结论。

共同约束：

- 保持 subject、status、数量、单位、原因编码、classification、Evidence 引用及 successfulScopes/failedScopes 的含义一致；保留事实、可能原因、未知项和 limitations，不得遗漏影响结论含义的内容。
- 不从原始用户消息、会话历史、模型知识或外部查询引入事实；不调用 Tool，不重新分析 evidences 或计算业务规则。
- 不新增建议；只有 Result 已承载的建议才可表达，且必须说明尚未执行。
- LLM 渲染失败、超时或输出违反上述约束时，丢弃其输出，以 `DeterministicAnswerRenderer` 渲染同一 Result；降级不得修改结构化字段、追加 UNKNOWN 或改变分析 status。
- Renderer 的输出只用于表达，不回流到 Assembler、分类或业务决策；HTTP/SSE 返回的结构化结论与渲染前保持一致。

## 16. AgentState / API Compatibility

AgentState 新增逻辑字段：

- `request_context`
- `analysis_request`
- `analysis_result`

保留 `answer` 以兼容现有 Chat API。ChatResponse 增加可选 `analysisResult`；非库存分析响应为 null。SSE done 事件增加可选 `analysisResult`，旧客户端忽略未知字段即可。

## 17. Trace Contract

必需关联键：`requestId`、`analysisId`、`toolCallId`、`evidenceId`、`conversationId`。日志中的 userId、tenantId、warehouseId 按安全策略脱敏；authorization 永不记录。

上述关联键按实际到达的处理阶段记录；Evidence Collection 前失败使用独立 `error.traceId` 关联诊断，不伪造尚未产生的 toolCallId 或 evidenceId。Error Trace 不支持业务结论。

Tool start/end、retry、Evidence collection、conflict、result assembly 都必须携带 requestId 和 analysisId。

