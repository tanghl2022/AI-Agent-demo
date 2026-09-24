import pytest

from mcp import Client

from wms_mcp.server import mcp


@pytest.mark.anyio
async def test_get_stock():

    async with Client(mcp) as client:

        result = await client.call_tool(
            "get_stock",
            {
                "material_code": "MAT001"
            }
        )

        print(result.structured_content)

        assert result.structured_content is not None