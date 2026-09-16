from collections.abc import Callable
from typing import Any
from dataclasses import asdict, is_dataclass

from langchain_core.tools import tool

from wms_agent.apps.warehouse.ports.errors import WmsClientError
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService

ToolResult = dict[str, Any]


async def _safe_query(query: Callable[[str], ToolResult], value: str) -> ToolResult:
    """统一转换 WMS 查询异常；不向模型伪造业务数据。"""
    try:
        result = await query(value)
        return asdict(result) if is_dataclass(result) else result
    except WmsClientError as error:
        return {"success": False, "error": str(error)}


def create_wms_tools(service: WmsQueryService) -> list:
    @tool
    async def query_stock(material_code: str) -> dict:
        """查询指定物料当前总库存和可用库存。"""
        return await _safe_query(service.query_stock, material_code)

    @tool
    async def query_inventory_detail(material_code: str) -> dict:
        """查询物料 totalQty、reservedQty、frozenQty 和 availableQty。"""
        return await _safe_query(service.query_inventory_detail, material_code)

    @tool
    async def query_location(material_code: str) -> dict:
        """查询指定物料当前所在库位。"""
        return await _safe_query(service.query_locations, material_code)

    return [query_stock, query_inventory_detail, query_location]
