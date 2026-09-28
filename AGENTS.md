# WMS Agent Engineering Rules

## 1. 项目目标

本项目用于构建企业级 WMS AI Agent。

核心技术：

- LangGraph
- Tool Calling
- MCP
- Java WMS API
- Agent Evaluation


## 2. 系统调用边界

标准调用链：

User
→ Main Agent
→ SubAgent / Capability
→ Tool Calling
→ MCP Server
→ Java WMS API
→ Database


禁止：

Agent → Database

MCP Server → Database

LLM → Database


## 3. Agent 职责

Agent 负责：

- 理解用户意图
- 信息分析
- 任务规划
- Tool 选择
- Tool 调用
- 结果解释

Agent 不负责：

- 核心业务规则
- 库存事务
- 状态机
- 权限最终判定
- 数据一致性


## 4. WMS Java Service 职责

确定性业务规则必须由 Java WMS Service 实现。

包括：

- 库存计算
- 库存预占
- 库存冻结
- 移库
- 出库确认
- 状态机
- 幂等
- 事务
- 权限校验


## 5. MCP 规则

MCP 是 AI 与 WMS 之间的能力适配层。

MCP：

可以：

- 定义 Tool
- 参数转换
- 调用 Java API
- 返回标准结果

禁止：

- 直接操作数据库
- 实现核心库存业务逻辑
- 绕过 WMS API


## 6. 写操作

所有高风险写操作必须：

Agent
→ Proposal
→ Human Approval
→ MCP
→ Java WMS API

禁止 Agent 自动执行：

- 库存扣减
- 库存调整
- 冻结
- 解冻
- 移库确认
- 出库确认
- 设备控制


## 7. 开发流程

任何非简单修改必须遵循：

DEFINE
→ DESIGN
→ G1
→ IMPLEMENT
→ VERIFY
→ G2


## 8. Implement 规则

Codex 实现代码时必须：

1. 阅读 behaviors.md
2. 阅读 decisions.md
3. 阅读 contracts.md
4. 阅读 tasks.md
5. 不得自行改变已经确认的 Behavior
6. 不得自行改变 Architecture Decision
7. 超出 Scope 时停止并报告


## 9. Test

修改业务代码必须增加 Unit Test。

修改 MCP Tool 必须增加 Contract Test。

修改 Agent：

必须运行 Agent Evaluation。

修改 Intent：

必须运行 Intent Evaluation。


## 10. Definition of Done

任务只有同时满足以下条件才算完成：

- Unit Test PASS
- Integration Test PASS
- MCP Contract Test PASS
- Agent Evaluation PASS
- Critical Evaluation Cases PASS
- Architecture Rule PASS
- 无未确认 Scope Change