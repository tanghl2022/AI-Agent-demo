# WMS Agent 架构设计与演进基线

> 文档定位：WMS Agent 项目的长期架构基线（Architecture Baseline）。  
> 使用方式：新增 Node、Tool、Capability、SubAgent、MCP、RAG、监控诊断等能力前，先用本文档校准职责和演进方向。

## 1. 文档目的

本文档记录 WMS Agent 项目的长期目标、核心架构、模块职责、设计原则与演进约束，避免学习新技术或增加新功能时发生架构漂移。

本文档不是不可修改的最终设计。任何重要架构调整应明确回答：

1. 为什么需要修改？
2. 解决什么实际问题？
3. 是否破坏已有职责边界？
4. 是否引入了不必要的复杂度？
5. 修改后是否更容易测试、维护、追踪和扩展？

## 2. 项目定位与长期目标

本项目不是普通的 WMS 聊天机器人。

长期目标：

> 构建面向 WMS 业务的企业级智能 Agent，使 Agent 能通过 Tool 调用 WMS 业务能力，并结合业务数据、日志、Trace、MQ、监控和代码信息形成可追溯证据链，对 WMS 业务问题进行查询、分析、诊断和受控执行。

长期能力演进：

```text
自然语言查询 WMS
        ↓
Tool Calling
        ↓
多 Tool 联合分析
        ↓
SubAgent 专业化分析
        ↓
Evidence 驱动分析
        ↓
业务异常诊断
        ↓
Log / Trace / Metric / MQ
        ↓
代码分析
        ↓
MCP 标准化能力接入
        ↓
企业级 WMS Agent
```

## 3. 当前架构基线

当前主调用链保持：

```text
Graph
  ↓
Node
  ↓
SubAgent（复杂分析场景）
  ↓
Tool
  ↓
Capability
  ↓
Service
  ↓
Java API
  ↓
WMS
```

核心原则：**当前架构不推倒重构，在现有主链上逐步增强。**

## 4. 长期目标架构

```text
                         User
                          │
                          ▼
                    FastAPI / SSE
                          │
                          ▼
                 ┌──────────────────┐
                 │    Main Agent    │
                 │ Intent / Routing │
                 └────────┬─────────┘
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   Inventory Agent    Order Agent    Troubleshoot Agent
          │               │                │
          └───────────────┼────────────────┘
                          │
                     Tool Calling
                          │
                          ▼
                 ┌──────────────────┐
                 │  Tool Registry   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Capability Layer │
                 └────────┬─────────┘
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
           Service    MCP Client    Knowledge
              │           │            │
              ▼           ▼            ▼
          Java API    MCP Server       RAG
              │           │
              ▼           ▼
             WMS      Observability
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
              Loki      Tempo    Prometheus
                          │
                          ▼
                  Evidence Collector
                          │
                          ▼
                     LLM Analysis
                          │
              ┌───────────┼──────────┐
              ▼           ▼          ▼
             SSE       Approval    Report
```

横切能力：

```text
PostgreSQL Checkpointer
Session / Thread
Authentication / Permission
Human-in-the-loop
Audit Log
Tool Execution Log
Tracing / Metrics
```

## 5. 分层职责

### 5.1 Graph

负责工作流编排、状态流转、条件路由、确定性流程以及 Human-in-the-loop。

Graph 不承担具体业务查询实现，也不应因为每增加一个业务查询就增加一个永久 Node。

### 5.2 Node

Node 是 LangGraph 中的流程节点，主要负责：读取 State、调用对应能力或 Agent、更新 State、控制流程结果。

**Node ≠ Tool。**

适合成为 Node 的典型情况：审批、明确的流程阶段、必须确定执行顺序的步骤、路由等。

### 5.3 Main Agent

Main Agent 负责“谁来处理”，包括意图识别、领域路由、上下文管理以及高层任务协调。

避免让 Main Agent 直接持有大量细粒度业务 Tool，防止形成 God Agent。

### 5.4 SubAgent

SubAgent 负责某个专业领域中的复杂自主分析，例如：

- `InventoryAnalysisSubAgent`
- `OrderAnalysisSubAgent`
- `TroubleshootingSubAgent`

SubAgent 可以根据问题自主选择 Tool、多轮调用 Tool、观察结果并继续补充证据，最后形成领域分析结果。

### 5.5 Tool

Tool 是暴露给 LLM 的可调用能力，负责：Tool Schema、参数定义、Description 和 LLM 调用入口。

例如：

```text
stock_query
reservation_query
frozen_stock_query
inbound_order_query
outbound_order_query
inventory_log_query
```

Tool 应保持薄层，不承载复杂业务实现。

### 5.6 Capability

Capability 是 Agent 层与具体实现之间的稳定业务能力抽象。

调用关系：

```text
Tool → Capability → Service
```

Capability 的价值在于让 Agent 与底层通信方式解耦。未来即使从 HTTP 改为 MCP，也可以保持业务能力接口稳定：

```text
Tool → Capability → HTTP Provider
                  ↘ MCP Provider
```

**引入 Tool Calling 或 MCP 后，不因为技术变化直接删除 Capability。**

### 5.7 Service

Service 负责外部系统访问和技术细节，例如：HTTP/Java API 调用、DTO 转换、异常处理、超时、重试等。

Service 不负责 Agent 推理和 Tool 选择。

## 6. Main Agent 与 SubAgent 的边界

原则：

> Main Agent 决定“谁处理”；SubAgent 决定“怎么处理”。

示例：

```text
用户：为什么 MAT001 可用库存这么少？
          ↓
Main Agent
          ↓
inventory_analysis
          ↓
InventoryAnalysisSubAgent
          ↓
stock_query
          ↓
发现预占异常
          ↓
reservation_query
          ↓
关联订单查询
          ↓
形成分析
```

## 7. Tool Registry

随着 Tool 增加，建立统一注册与分类机制：

```text
ToolRegistry
│
├── inventory
│   ├── stock_query
│   ├── reservation_query
│   ├── frozen_stock_query
│   └── inventory_log_query
│
├── order
│   ├── order_query
│   ├── inbound_order_query
│   └── outbound_order_query
│
├── warehouse
│   ├── location_query
│   └── container_query
│
└── observability
    ├── log_query
    ├── trace_query
    └── metric_query
```

每个 SubAgent 只获取职责范围内的 Tool，而不是默认获得所有 Tool。

## 8. Evidence 驱动原则

Agent 分析应尽可能建立在真实 Tool 返回结果上。

核心原则：

> **No Evidence, No Conclusion.**

基本链路：

```text
Tool Calling
     ↓
业务/技术数据
     ↓
Evidence 标准化
     ↓
Evidence Collector
     ↓
LLM Analysis
```

建议的标准 Tool 返回模型：

```json
{
  "tool": "stock_query",
  "status": "success",
  "source": "WMS",
  "query": {
    "materialCode": "MAT001"
  },
  "data": {
    "total": 120,
    "reserved": 85,
    "frozen": 10,
    "available": 25
  },
  "evidence_id": "EV-001",
  "timestamp": "..."
}
```

失败结果也必须明确表达失败，而不能被解释为业务事实：

```json
{
  "tool": "stock_query",
  "status": "failed",
  "source": "WMS",
  "error": "timeout",
  "evidence_id": "EV-001"
}
```

查询失败只能得出“当前无法获得该证据”，不能得出“库存不存在”等结论。

## 9. WMS 故障诊断的长期方向

未来 `TroubleshootingAgent` 同时获取两类证据。

业务证据：库存、订单、预占、冻结、入库、出库、库存流水、任务状态等。

技术证据：Application Log、RabbitMQ、Redis、MySQL、Trace、Metric、Java Code、Git Diff 等。

```text
             用户问题
                │
                ▼
      Troubleshooting Agent
                │
       ┌────────┴─────────┐
       ▼                  ▼
 Business Evidence   Technical Evidence
       │                  │
       └────────┬─────────┘
                ▼
        Evidence Collector
                │
                ▼
        Root Cause Analysis
```

目标示例：

```text
为什么订单 SO001 一直处于“创建中”？
        ↓
查订单状态
        ↓
查 MQ 消息
        ↓
查库存预占
        ↓
查应用日志
        ↓
查 Trace
        ↓
定位 Java 代码
        ↓
必要时查看 Git Diff
        ↓
形成可追溯证据链
        ↓
给出业务/技术原因
```

## 10. MCP 定位

MCP 是标准化 Agent 与外部 Tool / Resource 连接方式的基础设施之一，不是当前阶段的开发目标本身。

当前：

```text
Tool → Capability → Service → HTTP → Java API
```

未来可演进为：

```text
Tool → Capability → MCP Client → WMS MCP Server
```

原则：**不为了使用 MCP 而使用 MCP。先把 Tool Calling、Capability、Evidence 模型跑通，再根据真实集成需求引入。**

## 11. Observability 演进

后续逐步考虑接入：

- Prometheus → Metric
- Loki → Log
- Tempo → Trace
- RabbitMQ → Message Evidence
- Java Code / Git → Code Evidence

目标链路：

```text
业务异常
  ↓
业务数据
  ↓
日志
  ↓
Trace
  ↓
MQ
  ↓
代码
  ↓
Root Cause
```

## 12. 当前项目状态

| 模块 | 状态 |
|---|---|
| FastAPI / API | ✅ 已有 |
| SSE | ✅ 已有 |
| Main Graph | ✅ 已有 |
| Intent Recognition | ✅ 已有 |
| 库存查询 | ✅ 已有 |
| 库位查询 | ✅ 已有 |
| 审批 | ✅ 已有 |
| Capability | ✅ 已有 |
| Service / Java API | ✅ 已有 |
| InventoryAnalysisNode | ✅ 已有 |
| InventoryAnalysisSubAgent | ✅ 已有 |
| Tool Calling | 🟡 建设中 |
| Tool Registry | ⬜ 待建设 |
| PostgreSQL Checkpointer | 🟡 建设中 |
| Evidence Model | ⬜ 待建设 |
| Evidence Collector | ⬜ 待建设 |
| Observability | ⬜ 后续 |
| MCP | ⬜ 后续 |
| Code Agent | ⬜ 后续 |
| RAG | ⬜ 后续 |
| Scheduler | ⬜ 后续 |
| Email / 企业微信 | ⬜ 后续 |

## 13. 当前阶段的约束

当前不要因为看到新技术就同时引入：大量 MCP Server、复杂 Multi-Agent、Agent-to-Agent、完整 RAG 平台、知识图谱、复杂 Planner、几十个 Graph Node、全套 Prometheus/Loki/Tempo。

这些能力不是永久排除，而是按问题和阶段引入。

当前最高优先级：

```text
InventoryAnalysisSubAgent
          ↓
      Tool Calling
          ↓
    Inventory Tools
          ↓
     Tool Registry
          ↓
    Evidence Model
          ↓
  Evidence Collector
          ↓
库存异常分析闭环
```

## 14. 架构决策检查表

增加新模块前先判断：

1. 它解决什么真实问题？
2. 它属于 Node、Tool、Capability、Service 还是 SubAgent？
3. LLM 是否需要自主决定是否调用？若是，优先考虑 Tool。
4. 是否属于稳定业务能力？若是，考虑 Capability。
5. 是否只是外部系统访问细节？若是，考虑 Service / Provider。
6. 是否属于独立专业领域中的复杂推理？若是，考虑 SubAgent。
7. 是否属于必须确定执行顺序的流程步骤？若是，考虑 Node。
8. 是否已有层能够解决？如果有，不增加新抽象。

> 不因为学到了一个新概念，就给项目增加一个新层。

## 15. 项目成功标准

项目最终不以 Node、Agent、MCP、RAG 或框架数量衡量，而以能否完成以下闭环衡量：

```text
真实 WMS 问题
      ↓
理解问题
      ↓
选择正确专业 Agent
      ↓
自主选择正确 Tools
      ↓
获取真实业务数据
      ↓
形成 Evidence
      ↓
基于 Evidence 分析
      ↓
必要时继续获取技术证据
      ↓
定位业务原因 / 技术原因
      ↓
输出可追溯结论
      ↓
高风险操作进入 Approval
      ↓
受控执行
```

---

## 16. 文档维护规则

- 本文档记录“长期架构方向”，不记录具体 Sprint 任务；任务进度维护在 `roadmap.md`。
- 已确认的重要架构选择建议进一步使用 ADR 记录原因。
- 每完成一个重要阶段，更新“当前项目状态”。
- 如果实际实践证明本文档某项设计不合理，可以修改，但必须记录修改原因，而不是静默改变架构。
