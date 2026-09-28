
# D-001 Inventory Risk

## Goal

库存分析增加库存风险等级。


## Scope

包含：

- 库存风险计算
- MCP 返回风险等级
- Agent 展示风险分析


不包含：

- 自动补货
- 自动移库
- 库存预测


## Business Rule

availableRate =
availableQty / totalQty


HIGH:

availableRate < 10%


MEDIUM:

10% <= availableRate < 30%


LOW:

availableRate >= 30%