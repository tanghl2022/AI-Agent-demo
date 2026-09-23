# ADR-002：复杂领域分析采用 SubAgent

## 状态
Accepted

## 背景
库存查询可以通过确定性 Node 完成，但“为什么库存不足”“预占异常原因是什么”等问题通常需要多次查询不同数据，并根据中间结果动态决定下一步动作。

## 决策问题
复杂库存分析应该继续使用固定 Graph/Node 编排，还是交给专业 SubAgent 自主选择 Tool？

## 可选方案

### 方案 A：全部使用 Node + 固定 Graph
优点：
- 流程确定
- 易于预测和调试

缺点：
- 每增加一种分析路径都需要修改 Graph
- 分支数量会快速膨胀
- 难以处理根据中间结果动态决定下一步查询的场景

### 方案 B：专业 SubAgent + Tool Calling
优点：
- 可以根据问题和 Tool 返回结果动态选择下一步
- Main Graph 保持简洁
- 专业领域能力可以独立演进

缺点：
- 调试复杂度高于固定流程
- 需要限制 Tool 范围并建立 Evidence 机制

## 最终决策
复杂领域分析采用 SubAgent。

库存领域首先建设 `InventoryAnalysisSubAgent`。

Main Agent / Main Graph 负责“谁处理”，SubAgent 负责“怎么处理”。

## 决策原因
确定性工作流适合 Node；需要动态推理、多 Tool 联合调用的专业问题更适合 SubAgent。两者不互相替代。

## 影响
不为每一个业务查询建立一个新的分析 Node。SubAgent 只获取其领域所需的 Tool，避免形成拥有全部工具的 God Agent。

## 重新评估条件
如果某个 SubAgent 的执行流程长期完全固定、无需根据中间结果决策，应考虑将该流程下沉为确定性 Graph/Node。
