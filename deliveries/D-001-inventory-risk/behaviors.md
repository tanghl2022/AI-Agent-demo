
# Behaviors

## B1 HIGH Risk

Given:

totalQty = 100

availableQty = 5

When:

执行库存分析

Then:

riskLevel = HIGH


## B2 MEDIUM Risk

Given:

totalQty = 100

availableQty = 20

When:

执行库存分析

Then:

riskLevel = MEDIUM


## B3 LOW Risk

Given:

totalQty = 100

availableQty = 50

When:

执行库存分析

Then:

riskLevel = LOW


## B4 Zero Inventory

Given:

totalQty = 0

When:

执行库存分析

Then:

不得发生除零异常