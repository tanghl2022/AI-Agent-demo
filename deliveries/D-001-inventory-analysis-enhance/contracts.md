# D-001 库存异常原因分析增强 Contracts

## Status

- 阶段：DESIGN
- 状态：待 G1 审批
- 版本：`v1`

## 1. Contract Principles

1. 所有能力只读。
2. Java WMS 是库存事实、原因规则和最终权限的权威来源。
3. MCP 只做参数校验、协议适配、错误映射和 Evidence 包装。
4. Agent 只消费 Evidence，不修改 Tool 返回的确定性 assessment。
5. JSON 字段统一使用 `camelCase`；Python 内部模型可使用 `snake_case`，但边界序列化必须遵守本契约。

## 2. Trusted Request Context

以下信息由受信任的 API/运行时上下文注入，不属于 LLM Tool 参数：

| Header / Context | Required | Source | Rule |
|---|---:|---|---|
| `Authorization` | 是 | 已认证 Web/API 请求 | 仅转发，不记录明文 |
| `X-Request-Id` | 是 | Agent request context | 全链路保持不变 |
| `X-User-Id` | 是 | 已认证用户上下文 | LLM 不可覆盖 |
| `X-Tenant-Id` | 是 | 已认证租户上下文 | LLM 不可覆盖 |
| `X-Warehouse-Id` | 是 | 已授权仓库上下文 | LLM 不可覆盖 |

缺少任一必填上下文时，MCP Adapter 必须在调用前返回 `ERROR/INTERNAL_ERROR`，不得发起匿名或无范围查询。

## 3. Common Evidence Envelope

所有 MCP inventory tools 返回：

```json
{
  "evidenceId": "ev_01J...",
  "tool": "inventory_detail_query",
  "status": "SUCCESS",
  "source": "JAVA_WMS",
  "query": {
    "materialCode": "MAT001"
  },
  "data": {},
  "error": null,
  "observedAt": "2026-09-28T10:00:00+08:00",
  "requestId": "req-001"
}
```

### 3.1 Field Rules

| Field | Type | Required | Rule |
|---|---|---:|---|
| `evidenceId` | string | 是 | MCP 生成；一次请求内唯一 |
| `tool` | string | 是 | 必须等于实际 Tool 名称 |
| `status` | enum | 是 | `SUCCESS / NO_DATA / PARTIAL / FORBIDDEN / ERROR` |
| `source` | string | 是 | v1 固定为 `JAVA_WMS` |
| `query` | object | 是 | 仅包含业务查询参数，不含 Token |
| `data` | object/null | 是 | `SUCCESS/PARTIAL` 可有值；其他状态为 null |
| `error` | object/null | 是 | 失败状态必须有值；成功状态为 null |
| `observedAt` | RFC 3339 string/null | 是 | Java WMS 数据时间；无法取得时为 null |
| `requestId` | string | 是 | 等于受信任请求上下文中的 Request ID |

### 3.2 Error Object

```json
{
  "code": "UPSTREAM_TIMEOUT",
  "message": "库存服务查询超时",
  "retryable": true
}
```

`code` 仅允许：

- `INVALID_ARGUMENT`
- `NOT_FOUND`
- `FORBIDDEN`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `UPSTREAM_INVALID_RESPONSE`
- `INTERNAL_ERROR`

`message` 不得包含 Token、数据库信息、堆栈或未脱敏业务敏感数据。

## 4. Common Assessment

Java WMS 可以在各 Tool 的 `data.assessments` 返回确定性原因判断：

```json
{
  "reasonCode": "WMS_DEFINED_CODE",
  "reasonText": "由 WMS 返回的业务解释",
  "certainty": "CONFIRMED",
  "priority": 100,
  "evidenceRefs": ["reservation:R-001"]
}
```

| Field | Type | Required | Rule |
|---|---|---:|---|
| `reasonCode` | string | 是 | Java WMS 管理；MCP/Agent 不解释或创造新编码 |
| `reasonText` | string | 是 | Java WMS 返回的用户可读说明 |
| `certainty` | enum | 是 | `CONFIRMED / EXCLUDED / UNKNOWN` |
| `priority` | integer/null | 是 | 值越小越优先；没有业务顺序时为 null |
| `evidenceRefs` | string[] | 是 | 引用同一响应中稳定的业务记录标识 |

Agent 可输出 `POSSIBLE` 候选解释，但 `POSSIBLE` 不属于 Java WMS assessment，也不得写回 Tool 结果。

## 5. MCP Tool Contracts

### 5.1 `inventory_detail_query`

#### Input

```json
{
  "material_code": "MAT001"
}
```

- `material_code`: 必填，trim 后长度 `1..64`；空值返回 `INVALID_ARGUMENT`。

#### Java WMS API

```http
GET /api/wms/inventory/{materialCode}
```

#### Success Data

```json
{
  "materialCode": "MAT001",
  "totalQty": 100,
  "reservedQty": 30,
  "frozenQty": 10,
  "availableQty": 60,
  "assessments": []
}
```

所有数量由 Java WMS 返回。MCP 和 Agent 不重新计算 `availableQty`。

### 5.2 `inventory_reservation_query`

#### Input

```json
{
  "material_code": "MAT001"
}
```

#### Java WMS API

```http
GET /api/wms/inventory/{materialCode}/reservations
```

#### Success Data

```json
{
  "materialCode": "MAT001",
  "totalReservedQty": 30,
  "reservations": [
    {
      "reservationId": "R-001",
      "reservedQty": 30,
      "status": "WMS_DEFINED_STATUS",
      "businessType": "WMS_DEFINED_TYPE",
      "businessRef": "MASKED_OR_AUTHORIZED_REFERENCE",
      "createdAt": "2026-09-28T09:00:00+08:00"
    }
  ],
  "assessments": []
}
```

`status`、`businessType` 和 `businessRef` 的业务枚举与可见性由 Java WMS 管理。无预占记录返回 `NO_DATA/NOT_FOUND`，不得返回技术错误。

### 5.3 `inventory_freeze_query`

#### Input

```json
{
  "material_code": "MAT001"
}
```

#### Java WMS API

```http
GET /api/wms/inventory/{materialCode}/freezes
```

#### Success Data

```json
{
  "materialCode": "MAT001",
  "totalFrozenQty": 10,
  "freezes": [
    {
      "freezeId": "F-001",
      "frozenQty": 10,
      "status": "WMS_DEFINED_STATUS",
      "reasonCode": "WMS_DEFINED_REASON",
      "reasonText": "由 WMS 返回并允许展示的冻结原因",
      "createdAt": "2026-09-28T09:30:00+08:00"
    }
  ],
  "assessments": []
}
```

无冻结记录返回 `NO_DATA/NOT_FOUND`。

### 5.4 `location_query`

#### Input

```json
{
  "material_code": "MAT001"
}
```

#### Java WMS API

```http
GET /api/wms/inventory/location/{materialCode}
```

#### Success Data

```json
{
  "materialCode": "MAT001",
  "locations": [
    {
      "locationCode": "A01-01-01",
      "quantity": 60
    }
  ],
  "assessments": []
}
```

无库位数据返回 `NO_DATA/NOT_FOUND`。

## 6. HTTP-to-Evidence Mapping

| Java WMS Result | Evidence status | Error code | Retry |
|---|---|---|---:|
| 200，完整合法响应 | `SUCCESS` | null | 否 |
| 200，WMS 明确标记部分数据 | `PARTIAL` | WMS 提供的安全错误码 | 否 |
| 400 / 422 | `ERROR` | `INVALID_ARGUMENT` | 否 |
| 401 / 403 | `FORBIDDEN` | `FORBIDDEN` | 否 |
| 404 | `NO_DATA` | `NOT_FOUND` | 否 |
| timeout | `ERROR` | `UPSTREAM_TIMEOUT` | 是，最多 1 次 |
| connect error / 502 / 503 / 504 | `ERROR` | `UPSTREAM_UNAVAILABLE` | 是，最多 1 次 |
| 其他 5xx | `ERROR` | `UPSTREAM_UNAVAILABLE` | 否 |
| 2xx 但 schema 非法 | `ERROR` | `UPSTREAM_INVALID_RESPONSE` | 否 |
| MCP 内部未分类异常 | `ERROR` | `INTERNAL_ERROR` | 否 |

## 7. Backend MCP Port

应用层依赖以下抽象，而不直接依赖 MCP SDK：

```python
class InventoryEvidencePort(Protocol):
    async def query_inventory_detail(self, material_code: str) -> EvidenceEnvelope: ...
    async def query_reservations(self, material_code: str) -> EvidenceEnvelope: ...
    async def query_freezes(self, material_code: str) -> EvidenceEnvelope: ...
    async def query_locations(self, material_code: str) -> EvidenceEnvelope: ...
```

具体 MCP Client Adapter 位于 Integration 层，并由组合根注入。

## 8. InventoryAnalysisSubAgent Result

```json
{
  "status": "PARTIAL",
  "answer": "用户可读的证据化分析文本",
  "evidenceIds": ["ev_01J..."],
  "confirmedCauses": [
    {
      "reasonCode": "WMS_DEFINED_CODE",
      "reasonText": "由 WMS 确认的原因",
      "evidenceIds": ["ev_01J..."]
    }
  ],
  "possibleCauses": [],
  "unknowns": ["冻结证据查询失败，未完成该维度调查"]
}
```

### Result Status

- `SUCCESS`：所用 Tool 均成功，回答基于完整的计划内 Evidence；
- `PARTIAL`：至少一个 Tool 成功且至少一个计划内 Tool 未完成；
- `FAILED`：形成回答所需的 Tool 均失败或无可用 Evidence；
- `INSUFFICIENT_EVIDENCE`：Tool 调用完成或达到上限，但证据不足以确认原因。

### Answer Format

用户可读 `answer` 固定包含以下段落：

1. `调查范围`
2. `已确认事实`
3. `原因结论`
4. `未完成或未知项`
5. `建议（未执行）`，仅在存在建议时显示

`CONFIRMED`、`POSSIBLE`、`EXCLUDED` 必须使用明确措辞区分。没有 Java WMS `CONFIRMED` assessment 时，不得出现“根因已确认”等表述。

## 9. Agent State Contract

新增内部状态字段：

```text
analysis_status: SUCCESS | PARTIAL | FAILED | INSUFFICIENT_EVIDENCE | null
analysis_evidence_ids: list[string]
```

现有 `answer` 字段保持不变。`InventoryAnalysisNode` 输入使用 `user_message`，输出同时写入 `answer`、`analysis_status`、`analysis_evidence_ids`。

## 10. Security and Read-only Contract

InventoryAnalysisSubAgent 的 Tool Registry 必须精确等于第 5 节四个只读 Tool。启动时若发现写 Tool 或未知 Tool 被注入，装配必须失败并记录安全错误。

禁止的 Tool 至少包括：

- inventory freeze / unfreeze
- inventory deduction / adjustment
- stock movement execution
- inbound / outbound confirmation
- task mutation
- device control

## 11. Compatibility

- `QUERY_STOCK` 与 `QUERY_LOCATION` 固定节点的外部行为保持不变；
- Chat API 继续返回现有 `answer` 文本；
- 旧 MCP `get_stock` 在迁移期标记 deprecated，不再注册给 InventoryAnalysisSubAgent；
- 删除 deprecated Tool 必须另行评估外部消费者，不在本交付中执行。

