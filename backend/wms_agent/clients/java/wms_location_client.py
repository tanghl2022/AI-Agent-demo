import httpx

from wms_agent.models.wms_query_result import (
    LocationQueryItem,
    LocationQueryResult,
)

class WmsLocationClient:
    """
    WMS库位 HTTP Client。

    Agent 不直接操作库存数据库，
    所有库存写操作必须通过 Java WMS Business API。
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
    ):
        self.base_url = (
            base_url.rstrip("/")
        )

        self.timeout = timeout

    async def query_locations(
            self,
            material_code: str,
    ) -> LocationQueryResult:
        """
        查询Java WMS中的实时库存。

        查询属于只读操作，
        Agent不能直接查询MySQL，
        必须通过WMS业务API。
        """

        url = (
            f"{self.base_url}"
            f"/api/wms/inventory/location/{material_code}"
        )

        async with httpx.AsyncClient(
                timeout=self.timeout
        ) as client:
            response = await client.get(
                url
            )

        response.raise_for_status()

        data = response.json()

        raw_locations = data.get(
            "locations",
            [],
        )

        locations = []

        for item in raw_locations:
            # 兼容 Java 返回对象列表或简单库位编码列表。
            if isinstance(item, dict):
                location_code = (
                    item.get("locationCode")
                    or item.get("location_code")
                    or ""
                )
                quantity = int(
                    item.get(
                        "quantity",
                        0,
                    )
                )
            else:
                location_code = str(item)
                quantity = 0

            locations.append(
                LocationQueryItem(
                    location_code=location_code,
                    quantity=quantity,
                )
            )

        return LocationQueryResult(
            material_code=data[
                "materialCode"
            ],
            locations=locations,
        )
