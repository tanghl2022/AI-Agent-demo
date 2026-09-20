from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService


class InventoryDetailCapability:
    """
    库存明细查询能力。

    职责：
    1. 对 Agent 层暴露统一的库存明细查询能力；
    2. 屏蔽底层 WmsQueryService；
    3. 后续 Node、Tool、SubAgent 都通过 Capability 使用该能力。

    注意：
    Capability 不负责决定什么时候调用，
    也不负责 LLM Tool Calling。
    """

    def __init__(
        self,
        query_service: WmsQueryService,
    ):
        self._query_service = query_service

    async def execute(
        self,
        material_code: str,
    ) -> dict:
        """
        查询指定物料的库存详细信息。

        返回：
        totalQty
        reservedQty
        frozenQty
        availableQty
        """
        return await self._query_service.query_inventory_detail(
            material_code
        )