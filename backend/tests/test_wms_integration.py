"""使用内存 HTTP 传输验证真实 WMS 适配器，不恢复生产 Mock 客户端。"""
import json
import httpx
import pytest
from wms_agent.integrations.wms.inventory_client import WmsInventoryClient
from wms_agent.integrations.wms.location_client import WmsLocationClient
from wms_agent.apps.warehouse.ports.errors import WmsClientError
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService


async def test_query_clients_map_external_fields():
    def respond(request):
        if "/location/" in request.url.path:
            return httpx.Response(200, json={"materialCode": "MAT001", "locations": [
                {"locationCode": "A01", "quantity": 60}, "A02"]})
        return httpx.Response(200, json={"materialCode": "MAT001", "totalQty": 100,
                                      "reservedQty": 10, "frozenQty": 20, "availableQty": 70})
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(respond)) as http:
        service = WmsQueryService(WmsInventoryClient(http), WmsLocationClient(http))
        assert (await service.query_stock("MAT001")).available_qty == 70
        locations = await service.query_locations("MAT001")
        assert locations.locations[0].location_code == "A01"
        assert locations.locations[0].quantity == 60
        assert locations.locations[1].location_code == "A02"


async def test_freeze_passes_idempotency_key_and_preserves_business_rejection():
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(409, json={"message": "库存不足", "availableQty": 3})
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(respond)) as http:
        result = await WmsInventoryClient(http).freeze_inventory(
            idempotency_key="FREEZE_INVENTORY:f1", material_code="MAT001", quantity=20)
    assert requests == [{"idempotencyKey": "FREEZE_INVENTORY:f1", "materialCode": "MAT001", "quantity": 20}]
    assert not result.success
    assert not result.executed
    assert result.available_qty == 3
    assert result.message == "库存不足"


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_technical_http_failures_are_not_business_rejections(status):
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(
        lambda request: httpx.Response(status, text="upstream failed"))) as http:
        with pytest.raises(WmsClientError):
            await WmsInventoryClient(http).freeze_inventory(
                idempotency_key="f1", material_code="MAT001", quantity=20)
