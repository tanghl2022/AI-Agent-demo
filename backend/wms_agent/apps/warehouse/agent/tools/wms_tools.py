from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from typing import Any, Awaitable

from langchain_core.tools import tool

from wms_agent.apps.warehouse.agent.capabilities.inventory_detail import (
    InventoryDetailCapability,
)
from wms_agent.apps.warehouse.agent.capabilities.location_query import (
    LocationQueryCapability,
)
from wms_agent.apps.warehouse.agent.capabilities.stock_query import (
    StockQueryCapability,
)
from wms_agent.apps.warehouse.ports.errors import WmsClientError


ToolResult = dict[str, Any]


async def _safe_query(
    query: Callable[[str], Awaitable[Any]],
    value: str,
) -> ToolResult:
    """
    Tool 查询统一异常处理。

    主要职责：
    1. 调用 Capability；
    2. 将 dataclass 转换为 dict；
    3. 将 WMS 调用异常转换为 Tool 可识别结果；
    4. 不伪造任何业务数据。
    """

    try:
        result = await query(value)

        if is_dataclass(result):
            return asdict(result)

        return result

    except WmsClientError as error:
        return {
            "success": False,
            "error": str(error),
        }


def create_wms_tools(
    *,
    stock_query_capability: StockQueryCapability,
    inventory_detail_capability: InventoryDetailCapability,
    location_query_capability: LocationQueryCapability,
) -> list:
    """
    创建 WMS 查询类 Tools。

    注意：
    Tool 不直接依赖 Service。

    正确调用链：

        Tool
          ↓
        Capability
          ↓
        Service
          ↓
        Port
          ↓
        Java WMS API
    """

    @tool
    async def query_stock(
        material_code: str,
    ) -> dict:
        """
        查询指定物料当前库存。

        适用于需要获取物料库存数量、
        可用库存等基础库存信息的场景。
        """

        return await _safe_query(
            stock_query_capability.execute,
            material_code,
        )

    @tool
    async def query_inventory_detail(
        material_code: str,
    ) -> dict:
        """
        查询指定物料的库存详细组成。

        返回信息包括：
        totalQty：总库存
        reservedQty：预占库存
        frozenQty：冻结库存
        availableQty：可用库存

        当需要分析库存异常、
        有库存但无法出库等问题时，
        优先使用该工具。
        """

        return await _safe_query(
            inventory_detail_capability.execute,
            material_code,
        )

    @tool
    async def query_location(
        material_code: str,
    ) -> dict:
        """
        查询指定物料当前所在库位。

        当需要确认物料存放位置、
        库位分布时使用该工具。
        """

        return await _safe_query(
            location_query_capability.execute,
            material_code,
        )

    return [
        query_stock,
        query_inventory_detail,
        query_location,
    ]