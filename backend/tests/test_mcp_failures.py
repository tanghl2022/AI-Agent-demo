import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import pytest
from langchain_core.messages import AIMessage
from mcp import types
from mcp.server.fastmcp import FastMCP

from test_mcp_inventory import AnalysisModel, serve, upstream_ok, wms_tools
from wms_agent.config import load_settings
from wms_agent.integrations.mcp.client import discover_wms_tools, make_tool
from wms_agent.integrations.mcp.config import McpSettings
from wms_agent.integrations.mcp.result_mapper import map_result
from wms_agent.apps.warehouse.subagents.inventory_analysis.agent import InventoryAnalysisSubAgent
from wms_agent.apps.warehouse.agent.events.event_context import set_event_publisher, reset_event_publisher
from wms_agent.apps.warehouse.agent.events.event_publisher import AgentEventPublisher


async def test_discovery_fails_on_missing_tools_and_does_not_fallback():
    server = FastMCP("missing", stateless_http=True, json_response=True)
    async with serve(server.streamable_http_app()) as url:
        with pytest.raises(RuntimeError, match="工具发现失败"):
            await discover_wms_tools(McpSettings(url=url, timeout=2))


@pytest.mark.parametrize("raw", [
    types.CallToolResult(isError=True, content=[types.TextContent(type="text", text="private-key")]),
    types.CallToolResult(content=[types.TextContent(type="text", text="not-json")]),
    types.CallToolResult(content=[], structuredContent={"success": True, "data": {}}),
    types.CallToolResult(content=[], structuredContent={"success": False, "error": {"code": "SECRET", "message": "private-key"}}),
])
def test_invalid_or_error_mcp_result_never_becomes_evidence(raw):
    result = map_result(raw, "wms_query_stock", "M001")
    assert result["success"] is False
    assert result.get("data") is None
    assert "private-key" not in json.dumps(result)


def test_single_json_text_result_is_supported():
    payload = {"success": True, "data": {"material_code": "M001", "total_qty": 9,
        "reserved_qty": 1, "frozen_qty": 2, "available_qty": 6},
        "meta": {"source": "wms-api", "queried_at": datetime.now(timezone.utc).isoformat()}}
    result = map_result(types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(payload))]),
                        "wms_query_stock", "M001")
    assert result["data"]["available_qty"] == 6


async def test_invalid_arguments_are_rejected_before_network_call():
    tool = make_tool(types.Tool(name="wms_query_stock", inputSchema={"type": "object",
        "properties": {"material_code": {"type": "string"}}, "required": ["material_code"]}), McpSettings())
    for arguments in [{"material_code": " "}, {"material_code": 123}, {"material_code": "M001", "url": "http://other"}]:
        result = await tool.ainvoke(arguments)
        assert result["error"]["code"] == "INVALID_ARGUMENTS"


async def test_call_timeout_is_bounded_and_cancel_is_not_swallowed(monkeypatch):
    from wms_agent.integrations.mcp import client
    started = asyncio.Event()
    closed = []

    class SlowSession:
        async def call_tool(self, *args):
            started.set()
            await asyncio.Event().wait()

    @asynccontextmanager
    async def slow(settings):
        try:
            yield SlowSession()
        finally:
            closed.append(True)

    monkeypatch.setattr(client, "session", slow)
    remote = types.Tool(name="wms_query_stock", inputSchema={"type": "object",
        "properties": {"material_code": {"type": "string"}}, "required": ["material_code"]})
    tool = make_tool(remote, McpSettings(timeout=0.05))
    result = await tool.ainvoke({"material_code": "M001"})
    assert result["error"]["code"] == "MCP_TIMEOUT"
    started.clear()
    task = asyncio.create_task(make_tool(remote, McpSettings()).ainvoke({"material_code": "M001"}))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(closed) == 2


async def test_partial_failure_has_evidence_and_failed_event():
    def handler(request):
        return httpx.Response(403) if "/location/" in request.url.path else upstream_ok(request)
    model = AnalysisModel([AIMessage(content="", tool_calls=[
        {"id": "a", "name": "wms_query_stock", "args": {"material_code": "M001"}},
        {"id": "b", "name": "wms_query_locations", "args": {"material_code": "M001"}},
    ]), AIMessage(content="可用库存12，库位无法查询。[E1]")])
    publisher = AgentEventPublisher("r", "c")
    token = set_event_publisher(publisher)
    try:
        async with wms_tools(handler) as tools:
            result = await InventoryAnalysisSubAgent(chat_model=model, tools=tools).analyze("分析M001")
    finally:
        reset_event_publisher(token)
    assert result.status == "PARTIAL"
    assert len(result.evidence) == 1
    assert "无权" in result.answer
    events = [publisher.queue.get_nowait() for _ in range(publisher.queue.qsize())]
    assert events[-1].data["success"] is False
    assert events[-1].data["output"]["error"]["code"] == "FORBIDDEN"


async def test_all_failed_queries_do_not_allow_fabricated_model_answer():
    model = AnalysisModel([AIMessage(content="", tool_calls=[
        {"id": "a", "name": "wms_query_stock", "args": {"material_code": "M001"}},
    ]), AIMessage(content="库存999")])
    async with wms_tools(lambda req: httpx.Response(503)) as tools:
        result = await InventoryAnalysisSubAgent(chat_model=model, tools=tools).analyze("分析M001")
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.evidence == []
    assert "999" not in result.answer


def test_mcp_settings_are_loaded_and_secrets_not_repr(monkeypatch):
    monkeypatch.setenv("INVENTORY_TOOL_SOURCE", "mcp")
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:9999/mcp")
    monkeypatch.setenv("MCP_ACCESS_TOKEN", "secret-test")
    settings = load_settings(load_env_file=False)
    assert settings.inventory_tool_source == "mcp"
    assert settings.mcp.url.endswith(":9999/mcp")
    assert "secret-test" not in repr(settings)
    with pytest.raises(ValueError):
        McpSettings(timeout=float("nan"))
