# ADR-004：Agent 分析采用 Evidence-Driven 模式

## 状态
Accepted

## 背景
WMS Agent 将逐渐用于库存异常分析和业务故障诊断。如果 LLM 在数据缺失、Tool 调用失败或查询范围不足时自行补全事实，会降低分析结果的可信度和可追溯性。

## 决策问题
是否允许 Agent 仅根据自然语言上下文自由形成业务结论，还是要求重要分析结论能够关联真实 Tool 返回的 Evidence？

## 可选方案

### 方案 A：直接让 LLM 根据上下文分析
优点：
- 实现简单
- 输出灵活

缺点：
- 容易产生无数据支撑的结论
- 无法追踪结论来自哪个系统、哪次查询

### 方案 B：Evidence-Driven Analysis
优点：
- 结论可追溯
- 可以区分事实、推断和未知信息
- 有利于后续审计、故障诊断和人工复核

缺点：
- 需要统一 Tool 返回结构
- 需要 Evidence Model / Collector

## 最终决策
采用 Evidence-Driven Analysis。

核心原则：

**No Evidence, No Deterministic Conclusion.**

## 设计要求
Tool 返回结果逐步统一包含：
- tool
- status
- source
- query
- data / error
- evidence_id
- timestamp（适用时）

查询失败只能表示“当前未成功获得该数据”，不能被解释为“业务数据不存在”。

## 影响
后续建设 `Evidence Model` 和 `Evidence Collector`。InventoryAnalysisSubAgent 的重要结论应尽量能够关联一个或多个 Evidence。

## 重新评估条件
可以优化 Evidence 的具体数据结构，但不轻易取消“事实必须有来源”的原则。
