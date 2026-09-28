## 为什么写操作必须 Human Approval

# ADR-004：WMS Agent 写操作安全与 Human-in-the-loop

* Status: Accepted
* Date: 2026-09-28
* Decision Type: Safety Architecture
* Scope: WMS Write Operations

## 1. Context

WMS 涉及真实库存、任务和设备状态。

错误写操作可能造成：

* 账实不符
* 重复库存扣减
* 错误冻结
* 错误移库
* 出库异常
* 设备任务冲突
* 实物与系统状态不一致

LLM 输出具有概率性。

因此不能将 LLM Tool Calling 结果直接等同于业务执行命令。

## 2. Decision

LLM 不拥有 WMS 最终写权限。

所有高风险写操作必须采用：

```text
Understand
↓
Analyze
↓
Proposal
↓
Workflow
↓
Human Approval
↓
Controlled MCP Tool
↓
Java WMS API
↓
Business Validation
↓
Execution
```

## 3. High Risk Operations

至少包括：

* inventory freeze
* inventory unfreeze
* inventory deduction
* inventory adjustment
* stock movement
* outbound confirmation
* inbound confirmation
* task cancellation
* task force completion
* stacker crane control
* PLC command
* device control

## 4. Prepare / Execute Separation

高风险操作必须尽量拆分：

```text
prepare
```

与：

```text
execute
```

例如：

```text
prepare_freeze
```

只允许：

* 查询实时库存
* 校验参数
* 生成执行计划
* 计算影响范围
* 生成审批信息

禁止修改库存。

随后：

```text
WAITING_APPROVAL
```

Human Approval 通过后：

```text
execute_freeze
```

才允许调用受控业务 API。

## 5. Human Approval

审批信息至少包含：

* 操作类型
* 仓库
* 物料
* 库位
* 数量
* 原因
* 风险
* 操作用户
* Agent Session
* Request ID

审批必须可以：

```text
APPROVE
REJECT
```

拒绝后不得继续执行。

## 6. Authorization

Human Approval 不替代业务权限。

即使 Human 已批准：

```text
Java WMS API
```

仍必须执行：

* Authentication
* Authorization
* Tenant Validation
* Warehouse Validation
* Parameter Validation
* Business State Validation

## 7. Idempotency

所有写 Tool 必须携带：

```text
idempotency_key
```

例如：

```text
FREEZE_INVENTORY:{thread_id}
```

Agent 层负责生成并传递幂等上下文。

最终幂等约束由 Java WMS Service 保证。

禁止仅依赖 Agent Memory 判断：

> “这个任务好像执行过了。”

## 8. Transaction

Agent 不负责数据库事务。

MCP 不负责 WMS 核心事务。

事务边界必须位于：

```text
Java WMS Business Service
```

涉及 MQ 时由 WMS 系统采用：

* Local Transaction
* Outbox / Local Message Table
* Idempotent Consumer
* Compensation

等确定性机制保证一致性。

## 9. Audit

所有写操作必须记录：

```text
who
when
warehouse
tenant
session
agent
tool
parameters
approval
result
duration
error
```

敏感字段必须脱敏。

必须能够追踪：

```text
User Request
↓
Agent Decision
↓
Approval
↓
Tool Call
↓
WMS API
↓
Business Result
```

## 10. Failure Handling

如果发生：

* timeout
* MCP disconnect
* WMS API timeout
* Agent crash
* process restart

不得简单重新执行写操作。

必须使用：

```text
idempotency_key
+
business status query
```

确定真实执行状态。

无法确定时：

```text
UNKNOWN
```

并进入人工处理。

禁止 Agent 猜测执行成功。

## 11. Device Operations

涉及：

* PLC
* 堆垛机
* 输送线
* 机器人

时采用更严格规则。

Agent 默认只能：

```text
Analyze
Recommend
Prepare
```

真正设备指令必须经过受控调度系统。

LLM 不直接写 PLC Register。

## 12. Consequences

### Positive

* 降低 Agent 幻觉造成业务事故的风险
* 保证库存一致性
* 支持审计
* 支持重试恢复
* 明确 AI 与 WMS 的责任边界

### Negative

部分操作需要人工确认，自动化程度降低。

这是生产级 WMS Agent 必须接受的安全成本。

## 13. Revisit Conditions

可以根据业务风险等级逐步降低部分低风险操作的人工审批要求。

但以下原则长期保持：

> LLM 不直接修改库存数据库。

> 最终业务规则由确定性 WMS Service 控制。
