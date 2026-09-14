from typing import Protocol

from wms_agent.models.wms_query_result import StockQueryResult, LocationQueryResult
from wms_agent.models.wms_freeze_result import WmsFreezeResult


class InventoryClient(Protocol):
    """真实与模拟库存客户端共用的异步契约。"""

    async def query_stock(self, material_code: str) -> StockQueryResult: ...

    async def freeze_inventory(
        self, *, idempotency_key: str, material_code: str, quantity: int,
    ) -> WmsFreezeResult: ...


class LocationClient(Protocol):
    """真实与模拟库位客户端共用的异步契约。"""

    async def query_locations(self, material_code: str) -> LocationQueryResult: ...
