# WMS Agent 学习与开发 Roadmap

> 目标：让学习路线与项目演进保持一致，避免因为 MCP、RAG、Multi-Agent 等新概念不断切换方向。  
> 基线：以 `WMS_AGENT_ARCHITECTURE.md` 为架构约束。

## 0. 当前起点

当前已经具备：FastAPI、SSE、Main Graph、Intent Recognition、库存查询、库位查询、审批、Capability、Service、Java API、`InventoryAnalysisNode`、`InventoryAnalysisSubAgent`。

当前正在解决：Tool Calling 与 PostgreSQL Checkpointer。

当前主线不是扩充大量功能，而是完成第一个真正的 **“多 Tool + Evidence + SubAgent”业务分析闭环**。

---

# Phase 1：把 InventoryAnalysisSubAgent 真正跑通

## 目标

让 `InventoryAnalysisSubAgent` 能根据用户问题自主选择库存领域 Tool，而不是由 Graph 把每一步查询写死。

## 开发内容

优先建立以下 Tool：

```text
stock_query
reservation_query
frozen_stock_query
inbound_order_query
outbound_order_query
inventory_log_query
```

每个 Tool 通过 Capability 调用现有 Service / Java API。

调用链保持：

```text
InventoryAnalysisSubAgent
        ↓
Tool
        ↓
Capability
        ↓
Service
        ↓
Java API
```

## 学习重点

- Tool Calling 工作机制
- Tool Schema / 参数设计
- Tool Description 如何影响模型选 Tool
- Tool 返回结果设计
- 多轮 Tool Calling
- Agent 如何根据第一次查询结果决定第二次查询
- Tool 调用失败处理

## 完成标准

以下问题无需人为写死查询顺序：

> “MAT001 为什么可用库存这么少？”

Agent 至少能够自主完成类似：

```text
stock_query
      ↓
发现 reserved 较高
      ↓
reservation_query
      ↓
根据结果形成分析
```

**验收点：不是“能调用 Tool”，而是“能够根据 Tool 结果决定下一步”。**

---

# Phase 2：Tool Registry

## 目标

解决 Tool 数量增加后的注册、分类、依赖注入和 SubAgent 权限边界问题。

## 开发内容

建立类似：

```text
ToolRegistry
├── inventory
├── order
├── warehouse
└── observability（预留）
```

`InventoryAnalysisSubAgent` 只获得库存分析需要的 Tool。

## 学习重点

- Registry Pattern
- Dependency Injection
- Tool 生命周期
- Agent 与 Tool 解耦
- 最小权限 Tool 集合

## 完成标准

新增一个 Inventory Tool 时，不需要修改多个 Agent 初始化位置；SubAgent 能通过统一机制获得对应 Tool 集。

---

# Phase 3：Evidence Model

## 目标

让 Agent 的分析从“LLM 根据 Tool 原始返回自由发挥”升级为“基于标准化证据分析”。

## 开发内容

建立统一 Evidence 数据模型，至少包含：

```text
evidence_id
tool
status
source
query
data
error
timestamp
```

统一成功、空结果、失败、超时等状态语义。

## 学习重点

- Grounding
- Hallucination Control
- Structured Output
- Pydantic 数据模型
- 可追溯 AI 输出

## 完成标准

当库存 API 超时时，Agent 明确说明“证据获取失败/无法判断”，不能把超时解释为库存为 0 或库存不存在。

---

# Phase 4：Evidence Collector

## 目标

将一个分析任务中多个 Tool 返回的 Evidence 汇总，形成可追溯的分析上下文。

## 开发内容

```text
stock_query        → EV-001
reservation_query  → EV-002
order_query        → EV-003
                         ↓
                 Evidence Collector
                         ↓
                    LLM Analysis
```

考虑 Evidence 与 `thread_id / run_id / message_id` 的关联。

## 学习重点

- Agent State 设计
- LangGraph State
- Evidence 生命周期
- Checkpointer
- 审计与可观测性

## 完成标准

一次库存分析结束后，可以回答：

- 调用了哪些 Tool？
- 每个 Tool 查询了什么？
- 返回了什么？
- 哪些 Tool 失败？
- 最终结论使用了哪些 Evidence？

---

# Phase 5：库存异常诊断闭环

## 目标

从“库存查询”升级为真正的“库存异常分析”。

## 场景

至少覆盖：

```text
可用库存不足
预占异常
冻结库存异常
账面数量不一致
预计入库未到
大量待出库占用
库存流水异常
```

## 学习重点

- Domain Agent
- 多 Tool 推理
- 业务规则与 LLM 的边界
- 确定性计算与非确定性分析的边界

重要原则：数学计算、库存公式、状态校验等确定性逻辑尽量由代码完成，不让 LLM 猜。

## 完成标准

输入真实库存问题，系统能够输出：

```text
现象
↓
查询过程
↓
关键 Evidence
↓
可能原因/已确认原因
↓
无法确认的信息
↓
下一步建议
```

到这里，第一个 Agent 业务闭环才算真正完成。

---

# Phase 6：完善 Checkpointer / Session / Human-in-the-loop

## 目标

把当前 PostgreSQL Checkpointer 从“能连接”升级为完整的会话与流程恢复能力。

## 开发内容

- thread_id 规范
- Checkpoint 生命周期
- 多轮会话恢复
- Approval 状态恢复
- 服务重启后的流程恢复
- 会话隔离

## 学习重点

- LangGraph Checkpoint
- State Persistence
- Human-in-the-loop
- 幂等
- 恢复语义

## 完成标准

审批流程等待期间重启 Python 服务，恢复后仍能继续正确流程，而不是丢失 Agent 状态。

---

# Phase 7：TroubleshootingSubAgent

## 目标

从库存领域扩展到 WMS 业务异常诊断。

建议首先选择你熟悉的真实场景：

> “订单为什么一直停留在创建中？”

## 第一批业务 Tool

```text
order_query
inventory_reservation_query
local_message_query
inventory_task_query
operation_log_query
```

## 学习重点

- Troubleshooting Agent
- Hypothesis → Evidence → Verification
- 多领域 Tool 协作
- Root Cause Analysis

## 完成标准

Agent 可以通过业务数据定位问题属于：订单状态、库存预占、任务执行、消息状态等哪一层，而不是只复述订单信息。

---

# Phase 8：Observability Tools

## 目标

开始让 Agent 获取技术运行证据。

不要一口气全部接入，建议顺序：

```text
Application Log
      ↓
RabbitMQ
      ↓
Trace
      ↓
Metric
```

之后再根据现有基础设施考虑 Loki、Tempo、Prometheus。

## Tool 示例

```text
log_query
mq_message_query
trace_query
metric_query
```

## 学习重点

- Observability
- Logs / Metrics / Traces
- OpenTelemetry 基础
- Agentic Troubleshooting

## 完成标准

针对一个业务异常，Agent 可以同时引用：

```text
业务 Evidence
+
技术 Evidence
```

完成跨层诊断。

---

# Phase 9：Code Agent

## 目标

让故障诊断从运行数据继续深入源码。

## 第一批能力

```text
search_code
read_file
find_symbol
find_reference
git_log
git_diff
```

## 学习重点

- Code Search
- AST / Symbol
- Repository Context
- Git Evidence
- Code Agent

## 完成标准

能够形成类似：

```text
业务异常
 ↓
日志错误
 ↓
Trace 定位 Service
 ↓
搜索 Java 源码
 ↓
定位相关方法
 ↓
查看相关 Git Diff
 ↓
给出带代码证据的分析
```

注意：代码 Agent 的结论同样必须区分“代码事实”和“LLM 推断”。

---

# Phase 10：MCP

## 目标

当 Tool 数量、外部系统和 Agent 数量增长到现有直接集成方式明显不方便时，引入 MCP 做标准化能力接入。

## 优先改造对象

不要第一步就把所有 WMS API MCP 化。优先选择边界清晰的能力，例如：

```text
Observability MCP Server
Code MCP Server
Knowledge MCP Server
```

然后再评估 WMS MCP Server。

## 学习重点

- MCP Client / Server
- Tool / Resource / Prompt
- Transport
- 权限与安全边界
- MCP 与 Tool Calling 的关系

## 完成标准

Agent 上层 Tool/Capability 设计不因为底层从 HTTP 切换 MCP 而大规模重构。

---

# Phase 11：Knowledge / RAG

## 目标

解决 Agent 无法仅靠实时系统数据回答的企业知识问题。

典型内容：

```text
WMS 操作手册
业务规则
接口文档
异常处理 SOP
数据库说明
项目规范
历史故障案例
```

## 学习重点

- Embedding
- Chunking
- Retrieval
- Rerank
- Metadata Filter
- RAG Evaluation

## 完成标准

RAG 提供的是“知识证据”，并能与业务实时 Evidence 区分来源。

---

# Phase 12：Scheduler + Report + Notification

## 目标

在 Agent 查询/分析能力稳定后，实现无人触发的周期性智能任务。

例如：

```text
每天 08:00
   ↓
库存风险扫描
   ↓
Agent 调用 Tools
   ↓
Evidence
   ↓
风险分析
   ↓
生成报告
   ↓
邮件 / 企业微信
```

## 学习重点

- Scheduled Agent
- Background Job
- Report Generation
- Notification
- Agent Run Audit

## 完成标准

定时任务只是“触发 Agent”，而不是把 Agent 逻辑重新写进 Scheduler。

---

# Phase 13：企业级治理

## 目标

当核心功能稳定后补齐生产级治理能力。

重点包括：

```text
Authentication
Authorization
Tool Permission
Approval
Audit Log
Rate Limit
Timeout
Retry
Circuit Breaker
Token / Cost Tracking
Prompt Version
Tool Version
Agent Evaluation
Tracing
```

特别是写操作遵循：

```text
Read Tool
   ↓
Analysis
   ↓
Write Proposal
   ↓
Permission Check
   ↓
Human Approval（高风险）
   ↓
Execute
   ↓
Audit
```

---

# 总体路线图

```text
【现在】
InventoryAnalysisSubAgent
        │
        ▼
1. Tool Calling
        │
        ▼
2. Inventory Tools
        │
        ▼
3. Tool Registry
        │
        ▼
4. Evidence Model
        │
        ▼
5. Evidence Collector
        │
        ▼
6. 库存异常诊断闭环
        │
        ▼
7. Checkpointer / HITL 完善
        │
        ▼
8. TroubleshootingSubAgent
        │
        ▼
9. Log / MQ / Trace / Metric
        │
        ▼
10. Code Agent
        │
        ▼
11. MCP
        │
        ▼
12. RAG
        │
        ▼
13. Scheduler / Report / Notification
        │
        ▼
14. 企业级治理与评估
```

# 防偏航规则

学习过程中遇到一个新概念时，不立即加入项目，先问：

1. 它解决当前哪个真实问题？
2. 当前架构是否已经能解决？
3. 加入后能否形成一个可验收闭环？
4. 是现在需要，还是未来需要？
5. 会不会为了 Demo 技术丰富度牺牲项目清晰度？

如果没有明确答案，记录到 Backlog，不进入当前主线。

# 当前最近三个里程碑

## M1 — Tool Calling 闭环

完成 6 个库存 Tool，`InventoryAnalysisSubAgent` 能自主多轮调用。

## M2 — Evidence 闭环

统一 Evidence Model + Evidence Collector，任何重要结论都可以追溯到 Tool 结果。

## M3 — Inventory Troubleshooting MVP

实现“为什么库存不足/异常”的完整诊断场景，能够输出证据、原因、未知信息和建议。

**在 M1～M3 完成前，不把 MCP、RAG、Code Agent 作为主线开发。**
