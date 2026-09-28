"""Server 可独立测试，无模型和数据库依赖。"""
import httpx
import pytest
from wms_mcp.clients.wms_client import QueryError, WmsClient
from wms_mcp.server import create_server


async def test_server_exposes_readonly_tools_with_material_schema():
    tools = await create_server().list_tools()
    assert {tool.name for tool in tools} == {"wms_query_stock", "wms_query_locations"}
    assert all(tool.annotations.readOnlyHint for tool in tools)
    assert all(tool.inputSchema["required"] == ["material_code"] for tool in tools)


async def test_location_codes_without_quantity_remain_unknown():
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"materialCode": "M001", "locations": ["A-01"]})
    )) as http:
        result = await WmsClient(http).query("M001", locations=True)
    assert result["locations"] == [{"location_code": "A-01", "quantity": None}]


@pytest.mark.parametrize("payload", [
    {"materialCode": "M002", "totalQty": 4, "reservedQty": 0, "frozenQty": 0, "availableQty": 4},
    {"materialCode": "M001", "totalQty": True, "reservedQty": 0, "frozenQty": 0, "availableQty": 1},
])
async def test_wrong_material_or_invalid_numeric_data_is_rejected(payload):
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json=payload)
    )) as http:
        with pytest.raises(QueryError) as error:
            await WmsClient(http).query("M001")
    assert error.value.code == "INVALID_RESPONSE"


async def test_upstream_timeout_is_classified():
    def timeout(request):
        raise httpx.ReadTimeout("sensitive detail", request=request)
    async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(timeout)) as http:
        with pytest.raises(QueryError) as error:
            await WmsClient(http).query("M001")
    assert error.value.code == "UPSTREAM_TIMEOUT"
    assert "sensitive" not in str(error.value)
