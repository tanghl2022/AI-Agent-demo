
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService


class StockQueryCapability:
    """
    库存查询能力。
    """

    def __init__(self, query_service:WmsQueryService):
        self._query_service = query_service

    async def execute(
        self,
        material_code: str,
    ):
        return   await self._query_service.query_stock(
                material_code
            )
