# ADR-005：使用 Ports & Adapters 隔离 WMS 外部系统

* Status: Accepted
* Date: 2026-09-28
* Decision Type: Architecture
* Scope: WMS Agent Integration

## 1. Context

WMS Agent 需要访问多个外部能力：

* Java WMS
* MCP Server
* PostgreSQL Checkpointer
* Redis
* MQ
* 未来可能的 ERP / MES / WCS

如果业务代码直接依赖具体 HTTP Client、数据库 Client 或第三方 SDK，会导致业务逻辑与基础设施高度耦合。

例如不希望出现：

```text
Capability
→ httpx
→ WMS URL
```

或者：

```text
Node
→ requests
→ Java API
```

因此采用 Ports & Adapters 思想隔离外部系统。

## 2. Decision

Application / Domain 代码依赖抽象 Port。

Infrastructure / Integration 实现具体 Adapter。

标准依赖方向：

```text
Application
↓
Port
↑
Adapter
```

例如：

```text
Inventory Capability
↓
InventoryPort
↑
WmsInventoryClient
```

## 3. Port

Port 描述：

> 系统需要什么能力。

而不是：

> HTTP API 怎么调用。

例如：

```text
InventoryPort
```

表达：

```text
query_stock()

query_inventory_detail()

freeze_inventory()
```

但不关心：

* URL
* HTTP Method
* Token
* Timeout
* JSON 序列化

## 4. Adapter

Adapter 负责：

> 如何连接真实外部系统。

例如：

```text
WmsInventoryClient
```

负责：

* HTTP Client
* URL
* Authentication
* Timeout
* Serialization
* Error Mapping

## 5. Dependency Rule

Application Layer 禁止直接依赖：

```text
integrations
```

Business Layer 禁止直接创建：

```text
httpx.Client
requests.Session
```

外部依赖必须通过 Port 注入。

## 6. MCP Relationship

MCP Server 属于独立 Integration Boundary。

Agent 使用 MCP 时：

```text
SubAgent
↓
MCP Client Port
↓
MCP Adapter
↓
MCP Server
```

MCP Server 内部访问 Java WMS：

```text
MCP Tool
↓
WMS API Client
↓
Java WMS API
```

MCP 不能破坏 Ports & Adapters 的依赖方向。

## 7. Testing

Port 使业务测试可以使用：

```text
FakeInventoryPort
MockInventoryPort
```

而无需启动真实 WMS。

Integration Test 再验证：

```text
Real Adapter
→ WMS API
```

## 8. Architecture Enforcement

项目应通过 Architecture Test 自动检查依赖关系。

例如：

```text
apps
```

不得直接 import：

```text
integrations
```

Infrastructure 不得反向侵入 Application Business Logic。

架构规则不应该只存在于文档中。

必须逐步转化为：

```text
pytest
```

可执行约束。

## 9. Consequences

### Positive

* 降低 WMS API 耦合
* 提升测试能力
* 支持 Fake Adapter
* 方便更换外部实现
* Agent 核心代码保持稳定
* 支持 MCP 与传统 API 并存

### Negative

增加 Interface / Port / Adapter 文件数量。

对于简单接口会增加少量结构复杂度。

这是为了获得企业级系统长期可维护性而接受的成本。

## 10. Revisit Conditions

当系统规模显著缩小或整体 Integration Architecture 被替换时，可以重新评估。

在此之前，业务层不得绕过 Port 直接依赖具体 Infrastructure。
