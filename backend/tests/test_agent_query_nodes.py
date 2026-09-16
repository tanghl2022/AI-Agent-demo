from wms_agent.apps.warehouse.models.query import (
    StockQueryResult,
    LocationQueryResult,
    LocationQueryItem,
)

from wms_agent.apps.warehouse.agent.nodes.query.query_stock_node import (
    create_query_stock_node,
)

from wms_agent.apps.warehouse.agent.nodes.query.query_location_node import (
    create_query_location_node,
)


# ============================================================
# Fake库存查询客户端
# ============================================================

class FakeInventoryQueryClient:
    """
    单元测试不调用真正Java WMS。

    通过Fake Client验证：
        Agent Node是否正确使用WMS查询结果。
    """

    async def query_stock(
        self,
        material_code: str,
    ) -> StockQueryResult:

        return StockQueryResult(
            material_code=material_code,
            total_qty=120,
            reserved_qty=20,
            frozen_qty=10,
            available_qty=90,
        )


# ============================================================
# Fake库位查询客户端
# ============================================================

class FakeLocationQueryClient:

    async def query_locations(
        self,
        material_code: str,
    ) -> LocationQueryResult:

        return LocationQueryResult(
            material_code=material_code,
            locations=[
                LocationQueryItem(
                    location_code="A01-01-01",
                    quantity=50,
                ),
                LocationQueryItem(
                    location_code="A01-01-02",
                    quantity=40,
                ),
            ],
        )


async def test_query_stock_node_should_return_inventory_answer():
    """
    QUERY_STOCK节点应该：

    1. 获取material_code
    2. 调用WMS库存查询Client
    3. 将查询结果转换为用户可读answer
    4. 状态变成SUCCESS
    """

    client = FakeInventoryQueryClient()

    node = create_query_stock_node(
        client
    )

    state = {
        "thread_id": "agent-stock-001",
        "intent": "QUERY_STOCK",
        "status": "RUNNING",
        "material_code": "MAT001",
    }

    result = await node(state)

    assert result["status"] == "SUCCESS"

    assert result["active_workflow"] is None

    assert "MAT001" in result["answer"]

    assert "120" in result["answer"]

    assert "20" in result["answer"]

    assert "10" in result["answer"]

    assert "90" in result["answer"]


async def test_query_location_node_should_return_locations():
    """
    QUERY_LOCATION节点应该返回物料所在库位。
    """

    client = FakeLocationQueryClient()

    node = create_query_location_node(
        client
    )

    state = {
        "thread_id": "agent-location-001",
        "intent": "QUERY_LOCATION",
        "status": "RUNNING",
        "material_code": "MAT001",
    }

    result = await node(state)

    assert result["status"] == "SUCCESS"

    assert result["active_workflow"] is None

    assert "MAT001" in result["answer"]

    assert "A01-01-01" in result["answer"]

    assert "A01-01-02" in result["answer"]

    assert "50" in result["answer"]

    assert "40" in result["answer"]
