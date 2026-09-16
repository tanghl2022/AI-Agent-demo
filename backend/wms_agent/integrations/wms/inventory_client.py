"""WMS HTTP 适配器：解析外部字段并转换为仓储应用模型。"""
from urllib.parse import quote
import httpx
from wms_agent.apps.warehouse.models.freeze import WmsFreezeResult
from wms_agent.apps.warehouse.models.query import StockQueryResult
from wms_agent.apps.warehouse.ports.errors import WmsClientError


class WmsInventoryClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def query_stock(self, material_code: str) -> StockQueryResult:
        try:
            response = await self.http_client.get(f"api/wms/inventory/{quote(material_code, safe='')}")
            response.raise_for_status()
            data = response.json()
            return StockQueryResult(
                material_code=data["materialCode"], total_qty=int(data["totalQty"]),
                reserved_qty=int(data["reservedQty"]), frozen_qty=int(data["frozenQty"]),
                available_qty=int(data["availableQty"]),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise WmsClientError("WMS 库存查询失败或响应格式异常") from exc

    async def freeze_inventory(self, *, idempotency_key: str, material_code: str, quantity: int) -> WmsFreezeResult:
        try:
            response = await self.http_client.post("api/inventory/freeze", json={
                "idempotencyKey": idempotency_key, "materialCode": material_code, "quantity": quantity,
            })
            # 认证和限流等技术错误不伪装成正常业务拒绝。
            if response.status_code not in {400, 404, 409, 422}:
                response.raise_for_status()
            data = response.json()
            return WmsFreezeResult(
                success=response.is_success and bool(data.get("success")),
                executed=response.is_success and bool(data.get("executed")),
                idempotency_key=data.get("idempotencyKey", idempotency_key),
                material_code=data.get("materialCode", material_code),
                freeze_quantity=int(data.get("freezeQuantity", quantity)),
                total_qty=data.get("totalQty"), reserved_qty=data.get("reservedQty"),
                frozen_qty=data.get("frozenQty"), available_qty=data.get("availableQty"),
                message=data.get("message", "WMS 业务执行失败" if not response.is_success else ""),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise WmsClientError("WMS 库存冻结调用失败或响应格式异常") from exc
