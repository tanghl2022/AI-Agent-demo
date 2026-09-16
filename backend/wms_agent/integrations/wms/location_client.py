from urllib.parse import quote
import httpx
from wms_agent.apps.warehouse.models.query import LocationQueryItem, LocationQueryResult
from wms_agent.apps.warehouse.ports.errors import WmsClientError


class WmsLocationClient:
    """借用模块共享的 HTTP 客户端，不自行创建或关闭连接。"""

    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def query_locations(self, material_code: str) -> LocationQueryResult:
        try:
            response = await self.http_client.get(f"api/wms/inventory/location/{quote(material_code, safe='')}")
            response.raise_for_status()
            data = response.json()
            locations = []
            for item in data.get("locations", []):
                # 兼容 WMS 返回的库位对象和简单编码列表。
                locations.append(LocationQueryItem(
                    location_code=(item.get("locationCode") or item.get("location_code") or "") if isinstance(item, dict) else str(item),
                    quantity=int(item.get("quantity", 0)) if isinstance(item, dict) else 0,
                ))
            return LocationQueryResult(data["materialCode"], locations)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise WmsClientError("WMS 库位查询失败或响应格式异常") from exc
