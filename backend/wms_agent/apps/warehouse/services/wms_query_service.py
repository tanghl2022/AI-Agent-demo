from wms_agent.apps.warehouse.models.query import LocationQueryResult, StockQueryResult
from wms_agent.apps.warehouse.ports.inventory import InventoryPort
from wms_agent.apps.warehouse.ports.location import LocationPort


class WmsQueryService:
    """依赖业务协议，既可使用 WMS 实现，也可注入测试替身。"""

    def __init__(self, inventory_client: InventoryPort, location_client: LocationPort):
        self.inventory_client = inventory_client
        self.location_client = location_client

    async def query_stock(self, material_code: str) -> StockQueryResult:
        return await self.inventory_client.query_stock(material_code)

    async def query_locations(self, material_code: str) -> LocationQueryResult:
        return await self.location_client.query_locations(material_code)

    async def query_inventory_detail(self, material_code: str) -> dict:
        result = await self.query_stock(material_code)
        return dict(materialCode=result.material_code, totalQty=result.total_qty,
                    reservedQty=result.reserved_qty, frozenQty=result.frozen_qty,
                    availableQty=result.available_qty)
