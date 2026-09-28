"""两个只读工具共享结果封装，来源和时间由 Server 记录。"""
from datetime import datetime, timezone
from typing import Annotated
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from wms_mcp.clients.wms_client import QueryError

MaterialCode = Annotated[str, Field(min_length=1, max_length=128, pattern=r".*\S.*")]


def register_inventory_tools(server: FastMCP) -> None:
    async def query(ctx: Context, material_code: str, locations: bool) -> dict:
        meta = {"source": "wms-api", "queried_at": datetime.now(timezone.utc).isoformat()}
        try:
            client = ctx.request_context.lifespan_context
            data = await client.query(material_code.strip(), locations=locations)
            return {"success": True, "data": data, "error": None, "meta": meta}
        except QueryError as exc:
            return {"success": False, "data": None,
                    "error": {"code": exc.code, "message": str(exc)}, "meta": meta}

    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)

    @server.tool(annotations=annotations)
    async def wms_query_stock(material_code: MaterialCode, ctx: Context) -> dict:
        """查询物料当前总库存、预占、冻结和可用量。用于分析出库受限原因；不提供订单或质检状态，不执行写操作。"""
        return await query(ctx, material_code, False)

    @server.tool(annotations=annotations)
    async def wms_query_locations(material_code: MaterialCode, ctx: Context) -> dict:
        """查询物料所在库位与数量。quantity 为 null 表示未提供数量，不代表零；不能据此判断库位是否允许出库。"""
        return await query(ctx, material_code, True)
