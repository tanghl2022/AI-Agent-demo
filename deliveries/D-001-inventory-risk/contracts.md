
# Contracts

## WMS API

GET /api/inventory/{materialCode}/analysis


### Response

{
  "materialCode": "MAT001",
  "totalQty": 100,
  "availableQty": 20,
  "availableRate": 0.2,
  "riskLevel": "MEDIUM"
}


## MCP Tool

Name:

inventory_analysis


Input:

material_code: string


Output:

materialCode
totalQty
availableQty
availableRate
riskLevel