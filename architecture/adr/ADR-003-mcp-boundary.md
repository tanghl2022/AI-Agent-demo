## 为什么引入 MCP

# ADR-003：MCP Server 作为 Agent Tool 标准能力边界

* Status: Accepted
* Date: 2026-09-28
* Decision Type: Architecture
* Scope: WMS Agent / MCP Server

## 1. Context

WMS Agent 需要访问：

* 库存
* 库位
* 库存明细
* 订单
* 任务
* 设备
* SOP
* 其他 WMS 能力

如果每个 Agent 直接实现 HTTP Client，会导致：

* Agent 与 WMS API 强耦合
* Tool 定义分散
* 参数 Schema 不统一
* 权限难以集中治理
* Tool 审计困难
* 不利于其他 Agent 复用能力

因此项目采用 MCP Server 作为 Agent Tool 标准能力层。

## 2. Decision

MCP Server 是当前正式架构的一部分。

标准 Agentic 调用链：

```text
SubAgent
↓
Tool Calling
↓
MCP Client
↓
MCP Server
↓
Java WMS API
↓
WMS Business Service
```

## 3. MCP Responsibilities

MCP Server 负责：

### Tool Definition

定义：

* Tool Name
* Tool Description
* Input Schema
* Output Schema

### Protocol Adaptation

完成：

```text
MCP Request
↓
WMS REST API Request
```

以及：

```text
WMS Response
↓
MCP Tool Result
```

### Parameter Validation

执行 Tool 层基础参数校验。

### Error Mapping

将 WMS API 错误转换为 Agent 可以理解的结构化错误。

### Observability

记录：

* Tool Name
* Request ID
* User Context
* Warehouse Context
* Duration
* Result
* Error

敏感字段必须脱敏。

## 4. MCP Must NOT

MCP Server 不是 WMS Business Service。

禁止 MCP：

* 直接连接 WMS MySQL
* 直接修改库存表
* 自行实现库存事务
* 自行实现库存状态机
* 自行决定库存扣减规则
* 绕过 Java WMS API
* 绕过权限校验
* 绕过 Human Approval

禁止：

```text
MCP
→ MySQL
```

必须：

```text
MCP
→ Controlled WMS API
→ WMS Service
→ Database
```

## 5. Business Rule Ownership

确定性业务规则最终归：

```text
Java WMS Service
```

所有权示例：

```text
库存可用量计算       → Java WMS
库存冻结规则         → Java WMS
库存状态机           → Java WMS
最终权限判定         → Java WMS
业务幂等             → Java WMS
事务                 → Java WMS
```

MCP 不复制这些规则。

## 6. Read Tools

读 Tool 可以被授权的 SubAgent 直接使用。

例如：

```text
inventory_query

inventory_detail_query

location_query
```

仍然必须执行：

* 用户隔离
* 租户隔离
* 仓库隔离
* 权限校验

## 7. Write Tools

写 Tool 必须被视为高风险 Tool。

标准流程：

```text
Agent
↓
Proposal
↓
Workflow
↓
Human Approval
↓
MCP Write Tool
↓
Java WMS API
```

不得仅因为模型产生 Tool Call 就执行高风险业务写操作。

## 8. MCP vs Capability

MCP 和 Capability 不互相替代。

```text
Capability
=
Agent Application 内部能力抽象
```

```text
MCP
=
标准 Tool Protocol / External Capability Boundary
```

固定流程不强制 MCP 化。

需要 Agent 动态选择的业务能力优先通过 MCP Tool 暴露。

## 9. Consequences

### Positive

* Tool 标准化
* Agent 与 WMS 解耦
* Tool 可以跨 Agent 复用
* 权限与审计更容易治理
* 未来可以接入其他 Agent Runtime
* WMS API 仍保持业务权威

### Negative

增加：

* MCP Server
* MCP Client
* 网络调用
* Tool Schema 管理
* MCP 可用性治理

因此必须增加：

* timeout
* retry
* circuit breaker
* tracing
* metrics

## 10. Revisit Conditions

当 MCP 标准、Agent Runtime 或企业 API Gateway 架构发生重大变化时重新评估。

无论协议如何变化，WMS 核心业务规则不得迁移至 LLM。
