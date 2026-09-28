"""验证 WMS MCP 的结构化结果；远端错误正文不直接进入模型。"""
import json
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError


def failure(code: str, message: str) -> dict:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


class StockData(BaseModel):
    material_code: str = Field(min_length=1)
    total_qty: int = Field(strict=True, ge=0)
    reserved_qty: int = Field(strict=True, ge=0)
    frozen_qty: int = Field(strict=True, ge=0)
    available_qty: int = Field(strict=True, ge=0)


class LocationData(BaseModel):
    location_code: str = Field(min_length=1)
    quantity: int | None = Field(strict=True, ge=0)


class LocationsData(BaseModel):
    material_code: str = Field(min_length=1)
    locations: list[LocationData]


ERROR_MESSAGES = {
    "UNAUTHORIZED": "WMS 身份验证失败", "FORBIDDEN": "无权查询此库存数据",
    "NOT_FOUND": "WMS 接口或物料不存在，请核实", "RATE_LIMITED": "WMS 查询被限流",
    "UPSTREAM_ERROR": "WMS 服务查询失败", "UPSTREAM_UNAVAILABLE": "无法连接 WMS 服务",
    "UPSTREAM_TIMEOUT": "WMS 查询超时", "INVALID_RESPONSE": "WMS 返回数据不符合查询契约",
}


def map_result(result, tool_name: str, material_code: str) -> dict:
    if result.isError:
        return failure("MCP_TOOL_ERROR", "MCP 工具执行失败")
    try:
        payload = result.structuredContent
        if payload is None:
            texts = [part.text for part in result.content if part.type == "text"]
            if len(texts) != 1:
                raise ValueError("缺少唯一 JSON 结果")
            payload = json.loads(texts[0])
        if not isinstance(payload, dict):
            raise ValueError("结果必须是对象")
        if payload.get("success") is False:
            code = payload["error"]["code"]
            return failure(code if code in ERROR_MESSAGES else "MCP_TOOL_ERROR",
                           ERROR_MESSAGES.get(code, "MCP 工具执行失败"))
        if payload.get("success") is not True:
            raise ValueError("缺少成功标识")
        data = (StockData if tool_name == "wms_query_stock" else LocationsData).model_validate(payload["data"])
        if data.material_code != material_code.strip():
            raise ValueError("物料不匹配")
        meta = payload["meta"]
        queried_at = datetime.fromisoformat(meta["queried_at"])
        if meta["source"] != "wms-api" or queried_at.tzinfo is None:
            raise ValueError("来源或时间无效")
        return {"success": True, "data": data.model_dump(), "error": None,
                "meta": {"source": "wms-api", "queried_at": queried_at.isoformat(), "transport": "mcp"}}
    except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
        return failure("INVALID_RESPONSE", "MCP 返回结果不符合库存查询契约")
