## 为什么库存分析使用 SubAgent

# ADR-002：SubAgent 的使用边界

* Status: Accepted
* Date: 2026-09-28
* Decision Type: Architecture
* Scope: WMS Agent

## 1. Context

WMS Agent 同时存在：

* 固定 Node
* Capability
* Workflow
* Tool Calling
* SubAgent

如果缺少明确边界，很容易将所有新业务功能都实现为 Agent。

这会导致：

* Token 成本增加
* 行为不确定性增加
* 调试复杂度增加
* Evaluation 成本增加
* 业务规则失控

因此必须明确什么时候允许创建 SubAgent。

## 2. Decision

只有任务存在明显的动态推理和动态 Tool 选择需求时，才使用 SubAgent。

SubAgent 适用于：

```text
需要理解复杂目标
+
需要动态选择 Tool
+
可能需要多轮 Tool Calling
+
需要综合多个结果
+
最终需要 LLM 分析或解释
```

## 3. Current Example

InventoryAnalysisSubAgent 属于合理的 SubAgent。

典型流程：

```text
用户：

“帮我分析 MAT001 为什么可用库存这么低。”
```

Agent 可能需要：

```text
查询库存
↓
发现预占过高
↓
查询库存明细
↓
查询相关库位
↓
综合数据
↓
生成分析结论
```

调用路径并非完全固定，因此适合：

```text
SubAgent
→ Tool Calling
→ MCP
```

## 4. Scenarios That Should NOT Use SubAgent

以下场景原则上不创建 SubAgent：

### 单一确定性查询

例如：

```text
查询 MAT001 库存
```

优先：

```text
Node
→ Capability
```

### 固定业务流程

例如：

```text
库存冻结审批流程
```

优先：

```text
Workflow
```

而不是让 Agent 自主决定流程步骤。

### 确定性计算

例如：

```text
availableQty =
totalQty
- reservedQty
- frozenQty
```

必须由确定性业务服务完成。

### 权限判断

必须由确定性权限系统完成。

### 状态机

必须由 Java WMS / Workflow 控制。

## 5. Tool Permission

分析类 SubAgent 默认遵循：

```text
READ ONLY
```

InventoryAnalysisSubAgent 可以调用：

* inventory query
* inventory detail
* location query
* knowledge query

默认禁止直接调用：

* inventory freeze
* inventory unfreeze
* inventory deduction
* stock movement execution
* outbound confirmation
* device control

## 6. Write Operation

如果 SubAgent 分析结果产生写操作建议：

```text
SubAgent
↓
Proposal
↓
Workflow
↓
Human Approval
↓
Controlled Write Tool
```

禁止：

```text
SubAgent
↓
Write Tool
↓
直接执行
```

## 7. New SubAgent Admission Criteria

新增 SubAgent 前必须回答：

1. 普通 Java/Python 代码能否解决？
2. SQL 能否解决？
3. Capability 能否解决？
4. 固定 Workflow 能否解决？
5. 单次 Tool Calling 能否解决？
6. 是否真的需要动态 Tool 选择？
7. 是否真的需要多轮推理？

只有前五种方案明显不足时，才优先考虑 SubAgent。

## 8. Consequences

### Positive

* 控制 Agent 数量
* 降低系统复杂度
* 降低 Token 成本
* 提高确定性
* 降低幻觉风险
* 简化测试和运维

### Negative

部分流程需要显式 Workflow 和 Capability 设计，而不能全部交给 LLM。

这是有意接受的约束。

## 9. Revisit Conditions

当模型 Tool Calling 稳定性、成本和可观测性发生重大变化时，可以重新评估本 ADR。

但 WMS 核心业务规则仍不得直接交由 LLM 控制。
