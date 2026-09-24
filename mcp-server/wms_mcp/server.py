from mcp.server import MCPServer


# ============================================================
# 创建 MCP Server
# ============================================================

mcp = MCPServer("wms-mcp-server")


# ============================================================
# MCP Tool：库存查询
# ============================================================

@mcp.tool()
async def get_stock(material_code: str) -> dict:
    """
    查询指定物料的库存汇总信息。

    Args:
        material_code:
            WMS 中的物料编码，例如 MAT001。

    Returns:
        物料库存汇总信息，包括：
        - 总库存
        - 可用库存
        - 预占库存
        - 冻结库存
    """

    # V1 第一阶段先返回模拟数据，
    # 用于验证 MCP Tool 是否能够正常发现和调用。
    return {
        "material_code": material_code,
        "total_qty": 120,
        "available_qty": 25,
        "reserved_qty": 85,
        "frozen_qty": 10
    }