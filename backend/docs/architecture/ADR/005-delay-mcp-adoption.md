# ADR-005：当前阶段暂缓大规模引入 MCP

## 状态
Accepted

## 背景
MCP 可以标准化 Agent 与外部 Tool / Resource 的连接方式，但当前 WMS Agent 仍处于 Tool Calling、InventoryAnalysisSubAgent 和 Evidence 闭环建设阶段。

## 决策问题
是否现在将现有 Java API / Service 大规模改造成 MCP 架构？

## 可选方案

### 方案 A：立即全面 MCP 化
优点：
- 提前学习和实践 MCP
- 外部能力接口更加标准化

缺点：
- 会同时引入新的协议和基础设施复杂度
- 容易打断当前 Tool Calling / Evidence 主线
- MCP 本身不能解决 Agent 如何选择 Tool、如何分析证据的问题

### 方案 B：暂缓 MCP，先完成业务闭环
优点：
- 优先验证 Agent 的核心业务价值
- 可以先稳定 Tool、Capability、Evidence 边界
- 后续 MCP 接入目标更加明确

缺点：
- 短期仍主要使用现有 HTTP / Java API

## 最终决策
当前阶段采用方案 B。

优先完成：

`InventoryAnalysisSubAgent → Tool Calling → Inventory Tools → Tool Registry → Evidence → Inventory Troubleshooting MVP`

完成核心闭环后，再评估 MCP。

## 决策原因
MCP 主要解决能力接入标准化问题，不替代 Tool Calling、业务建模、Evidence 和 Agent 推理。当前更重要的是先把这些核心机制跑通。

## 影响
现阶段继续允许：

`Tool → Capability → Service → Java API`

未来可演进为：

`Tool → Capability → MCP Client → MCP Server`

不因学习 MCP 而推倒现有架构。

## 重新评估条件
满足以下条件后重新评估：
1. Tool Calling 闭环稳定；
2. Tool Registry 基本形成；
3. Evidence 模型稳定；
4. 出现多个外部系统需要统一接入；
5. MCP 能明确降低集成成本或提升能力复用。
