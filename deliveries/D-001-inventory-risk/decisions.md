
# Architecture Decisions

## D1 风险计算位置

### Options

A. LLM

B. Python SubAgent

C. Java WMS


### Decision

Java WMS


### Reason

库存风险属于确定性业务规则。

LLM 不应该负责确定性业务计算。


## D2 Agent Responsibility

InventoryAnalysisSubAgent：

负责：

- 获取库存数据
- 调用分析 Tool
- 解释风险等级

不负责：

- 自行计算风险等级