from dataclasses import replace
from wms_agent.clients.errors import WmsClientError

from wms_agent.models.wms_query_result import StockQueryResult, LocationQueryResult, LocationQueryItem
from wms_agent.models.wms_freeze_result import WmsFreezeResult


class MockWmsClient:
    """模拟外部 WMS，审批逻辑由共用工作流负责。"""

    def __init__(self):
        # 每个实例独立保存数据，避免测试互相污染。
        self._stocks = {
            "MAT001": StockQueryResult("MAT001", 120, 20, 10, 90),
            "MAT002": StockQueryResult("MAT002", 80, 10, 5, 65),
        }
        self._locations = {
            "MAT001": [LocationQueryItem("A01-01-01", 60), LocationQueryItem("A01-01-02", 60)],
            "MAT002": [LocationQueryItem("B02-03-01", 80)],
        }
        self._executions: dict[str, WmsFreezeResult] = {}

    async def query_stock(self, material_code: str) -> StockQueryResult:
        code = material_code.upper()
        if code not in self._stocks:
            raise WmsClientError(f"物料不存在: {material_code}")
        return self._stocks[code]

    async def query_locations(self, material_code: str) -> LocationQueryResult:
        stock = await self.query_stock(material_code)
        return LocationQueryResult(stock.material_code, list(self._locations[stock.material_code]))

    async def freeze_inventory(
        self, *, idempotency_key: str, material_code: str, quantity: int,
    ) -> WmsFreezeResult:
        code = material_code.upper()
        previous = self._executions.get(idempotency_key)
        if previous is not None:
            if (previous.material_code, previous.freeze_quantity) != (code, quantity):
                return replace(previous, success=False, executed=False, message="幂等键参数不一致")
            return replace(previous, executed=False)

        stock = self._stocks.get(code)
        # 模拟远端写入约束，不在这里实现审批流程。
        success = bool(idempotency_key) and stock is not None and 0 < quantity <= stock.available_qty
        if success:
            stock = replace(stock, frozen_qty=stock.frozen_qty + quantity,
                            available_qty=stock.available_qty - quantity)
            self._stocks[code] = stock
        result = WmsFreezeResult(
            success=success, executed=success, idempotency_key=idempotency_key,
            material_code=code, freeze_quantity=quantity,
            total_qty=stock.total_qty if stock else None,
            reserved_qty=stock.reserved_qty if stock else None,
            frozen_qty=stock.frozen_qty if stock else None,
            available_qty=stock.available_qty if stock else None,
            message="模拟冻结成功" if success else "参数无效、物料不存在或库存不足",
        )
        if success:
            self._executions[idempotency_key] = result
        return result
