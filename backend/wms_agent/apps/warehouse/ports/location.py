from typing import Protocol
from wms_agent.apps.warehouse.models.query import LocationQueryResult


class LocationPort(Protocol):
    """仓储应用需要的库位查询能力。"""

    async def query_locations(self, material_code: str) -> LocationQueryResult: ...
