from wms_agent.apps.warehouse.services import wms_query_service


class LocationQueryCapability:
    """
    库位查询能力。
    """

    def __init__(self, query_service):
        self._query_service = query_service

    async def execute(
        self,
        material_code: str,
    ):
        return  await wms_query_service.query_locations(
                material_code
            )

