## 为什么保留 Capability

# ADR-001：保留 Capability 作为稳定业务能力层

* Status: Accepted
* Date: 2026-09-28
* Decision Type: Architecture
* Scope: WMS Agent Backend

## 1. Context

WMS Agent 当前包含以下主要结构：

```text
Graph
→ Node
→ Capability
→ Application Service
→ Port / MCP
→ WMS API
```

随着系统逐步增加 LangGraph Node、SubAgent、Tool Calling 和 MCP Server，需要明确 Capability 是否仍然有存在价值。

一个可选方案是删除 Capability，让 Node、SubAgent 或 Tool 直接调用 Service、MCP 或外部 WMS API。

这种方式代码更少，但会导致 Agent 编排逻辑与业务能力实现产生较强耦合。

## 2. Decision

保留 Capability 层。

Capability 定义 WMS Agent 内部稳定的业务能力边界。

例如：

```text
StockQueryCapability

LocationQueryCapability

InventoryDetailCapability
```

Capability 不等同于：

* LangGraph Node
* MCP Tool
* REST API
* Application Service
* SubAgent

Capability 表示的是：

> WMS Agent 系统内部可以复用的业务能力。

## 3. Responsibilities

Capability 可以负责：

* 输入参数标准化
* 调用 Application Service
* 组合多个底层查询能力
* 输出统一业务模型
* 隐藏底层接口差异

Capability 不负责：

* LangGraph 状态跳转
* LLM 推理
* Prompt 管理
* Tool 自主选择
* 数据库操作
* WMS 核心事务
* WMS 状态机

## 4. Node 与 Capability 的边界

Node 属于工作流编排层。

```text
Node
=
Workflow Adapter
```

Capability 属于业务能力层。

```text
Capability
=
Reusable Application Capability
```

因此允许：

```text
Node
→ Capability
```

但不应该将大量业务能力直接实现到 Node 中。

Node 应尽可能保持轻量。

## 5. Capability 与 MCP 的关系

MCP Server 已经作为正式架构的一部分。

但 MCP 的引入不意味着 Capability 必须删除。

两者解决的问题不同：

```text
Capability
=
内部业务能力抽象

MCP
=
Agent Tool 标准协议与能力暴露边界
```

固定确定性流程可以直接使用 Capability。

需要 Agent 动态 Tool Calling 的能力可以通过 MCP 暴露。

禁止为了统一形式而强制：

```text
所有 Capability
→ MCP
```

## 6. Consequences

### Positive

* Node 保持轻量
* 业务能力可以复用
* 降低 LangGraph 与业务代码耦合
* 方便单元测试
* 方便未来替换 Agent Framework
* Capability 可以同时被 Workflow、Node 等组件使用

### Negative

增加了一层抽象。

对于非常简单的查询能力可能产生少量样板代码。

这是为了获得长期架构稳定性而接受的成本。

## 7. Architecture Rule

推荐：

```text
Graph
→ Node
→ Capability
→ Service
```

禁止：

```text
Node
→ Database
```
