from dataclasses import asdict
from wms_agent.clients.contracts import InventoryClient, LocationClient
from wms_agent.models.wms_query_result import StockQueryResult


class WmsQueryService:
    def __init__(self, client: InventoryClient, location_client: LocationClient):
        self.client = client
        self.location_client = location_client

    async def query_stock(self, material_code: str) -> StockQueryResult:
        return await self.client.query_stock(material_code)

    async def query_inventory_detail(self, material_code: str) -> dict:
        # 兼容工具层字段；底层统一使用库存查询接口。
        result = await self.query_stock(material_code)
        return dict(materialCode=result.material_code, totalQty=result.total_qty,
                    reservedQty=result.reserved_qty, frozenQty=result.frozen_qty,
                    availableQty=result.available_qty)

    async def query_location(self, material_code: str) -> dict:
        return asdict(await self.location_client.query_locations(material_code))
