"""统一只读工具执行事件；保持业务层不依赖 MCP 实现。"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError
from wms_agent.apps.warehouse.agent.events.event_context import get_event_publisher
from wms_agent.apps.warehouse.agent.events.event_types import AgentEventType


async def execute_tool(tool, name: str, arguments: dict, *, timeout: float) -> dict:
    publisher = get_event_publisher()
    call_id = str(uuid.uuid4())
    started = time.perf_counter()
    common = {"toolName": name, "toolCallId": call_id,
              "transport": (getattr(tool, "metadata", None) or {}).get("transport", "local")}
    if publisher:
        await publisher.publish(AgentEventType.TOOL_START, node="inventory_analysis", status="RUNNING",
                                data={**common, "args": arguments})
    result = {"success": False, "error": {"code": "CANCELLED", "message": "工具调用已取消"}}
    try:
        if tool is None:
            result = {"success": False, "error": {"code": "UNKNOWN_TOOL", "message": "未提供此查询工具"}}
        else:
            async with asyncio.timeout(timeout):
                raw = await tool.ainvoke(arguments)
            if not isinstance(raw, dict):
                raise ValueError("工具结果必须为对象")
            if raw.get("success") is False:
                error = raw.get("error")
                result = raw if isinstance(error, dict) else {
                    "success": False, "error": {"code": "QUERY_FAILED", "message": "业务查询失败，未取得数据"}}
            else:
                result = {"success": True, "data": raw.get("data", raw),
                          "meta": raw.get("meta") or {"source": "wms-api", "queried_at": datetime.now(timezone.utc).isoformat()}}
    except TimeoutError:
        result = {"success": False, "error": {"code": "TOOL_TIMEOUT", "message": "工具查询超时"}}
    except ValidationError:
        result = {"success": False, "error": {"code": "INVALID_ARGUMENTS", "message": "工具参数不符合查询要求"}}
    except Exception:
        result = {"success": False, "error": {"code": "TOOL_FAILED", "message": "工具查询失败，未取得有效数据"}}
    finally:
        if publisher:
            await publisher.publish(AgentEventType.TOOL_END, node="inventory_analysis",
                status="SUCCESS" if result["success"] else "FAILED",
                data={**common, "success": result["success"], "output": result,
                      "durationMs": max(0, int((time.perf_counter() - started) * 1000)),
                      "summary": "查询完成" if result["success"] else result["error"]["message"]})
    return result
