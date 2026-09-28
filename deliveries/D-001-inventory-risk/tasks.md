
# Implementation Tasks

## T1

Java WMS 增加：

InventoryRiskLevel enum


## T2

InventoryAnalysisService 增加：

calculateRiskLevel()


Depends:

T1


## T3

Inventory Analysis API 返回 riskLevel


Depends:

T2


## T4

MCP inventory_analysis Tool 增加 riskLevel


Depends:

T3


## T5

InventoryAnalysisSubAgent 消费 riskLevel


Depends:

T4


## T6

增加 Unit Test


Depends:

T2


## T7

增加 Agent Evaluation Cases


Depends:

T5