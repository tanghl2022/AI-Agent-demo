from typing import Protocol
from wms_agent.apps.warehouse.models.query import StockQueryResult
from wms_agent.apps.warehouse.models.freeze import WmsFreezeResult


class InventoryPort(Protocol):
    """外部库存系统需要满足的异步契约。"""

    async def query_stock(self, material_code: str) -> StockQueryResult: ...

    async def freeze_inventory(self, *, idempotency_key: str, material_code: str, quantity: int) -> WmsFreezeResult: ...
