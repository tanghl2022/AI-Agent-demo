"""真实 Streamable HTTP 协议；仅 Java HTTP 和模型边界使用可控替身。"""
import asyncio
import json
import socket
from contextlib import asynccontextmanager

import httpx
import pytest
import uvicorn
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


@asynccontextmanager
async def serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="on", ws="none"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("测试服务器未启动")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, 10)
        finally:
            sock.close()


@asynccontextmanager
async def wms_tools(handler):
    from wms_mcp.server import create_server
    from wms_mcp.config import ServerSettings
    from wms_agent.integrations.mcp.client import discover_wms_tools
    from wms_agent.integrations.mcp.config import McpSettings

    @asynccontextmanager
    async def upstream():
        async with httpx.AsyncClient(base_url="http://wms/", transport=httpx.MockTransport(handler)) as client:
            yield client

    server = create_server(ServerSettings(), http_client_factory=upstream)
    async with serve(server.streamable_http_app()) as url:
        yield await discover_wms_tools(McpSettings(url=url, timeout=3))


def upstream_ok(request):
    if "/location/" in request.url.path:
        return httpx.Response(200, json={"materialCode": "M001", "locations": [
            {"locationCode": "A-01", "quantity": 12}]})
    return httpx.Response(200, json={"materialCode": "M001", "totalQty": 42,
        "reservedQty": 20, "frozenQty": 10, "availableQty": 12})


async def test_mcp_discovers_only_read_tools_and_returns_real_upstream_values():
    async with wms_tools(upstream_ok) as tools:
        by_name = {tool.name: tool for tool in tools}
        assert set(by_name) == {"wms_query_stock", "wms_query_locations"}
        stock = await by_name["wms_query_stock"].ainvoke({"material_code": "M001"})
        locations = await by_name["wms_query_locations"].ainvoke({"material_code": "M001"})
        assert stock["data"]["available_qty"] == 12
        assert stock["data"]["total_qty"] == 42
        assert stock["meta"]["source"] == "wms-api"
        assert stock["meta"]["queried_at"]
        assert locations["data"]["locations"] == [{"location_code": "A-01", "quantity": 12}]


@pytest.mark.parametrize("status,code", [(403, "FORBIDDEN"), (404, "NOT_FOUND"), (429, "RATE_LIMITED"), (500, "UPSTREAM_ERROR")])
async def test_upstream_errors_are_not_exposed_as_inventory(status, code):
    async with wms_tools(lambda req: httpx.Response(status, text="private-token-db-error")) as tools:
        result = await tools[0].ainvoke({"material_code": "M001"})
        assert result["success"] is False
        assert result["error"]["code"] == code
        assert result.get("data") is None
        assert "private-token" not in json.dumps(result)


async def test_bad_upstream_payload_is_rejected_instead_of_fabricating_zero():
    async with wms_tools(lambda req: httpx.Response(200, json={"materialCode": "M001"})) as tools:
        result = await tools[0].ainvoke({"material_code": "M001"})
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_RESPONSE"


class AnalysisModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.messages = list(messages)
        return next(self.responses)


async def test_analysis_uses_question_evidence_and_paired_events():
    from wms_agent.apps.warehouse.subagents.inventory_analysis.agent import InventoryAnalysisSubAgent
    from wms_agent.apps.warehouse.agent.nodes.agent.inventory_analysis import InventoryAnalysisNode
    from wms_agent.apps.warehouse.agent.events.event_context import set_event_publisher, reset_event_publisher
    from wms_agent.apps.warehouse.agent.events.event_publisher import AgentEventPublisher

    model = AnalysisModel([
        AIMessage(content="", tool_calls=[
            {"id": "s1", "name": "wms_query_stock", "args": {"material_code": "M001"}},
            {"id": "l1", "name": "wms_query_locations", "args": {"material_code": "M001"}},
        ]), AIMessage(content="预占20，冻结10，可用12；库位A-01。[E1][E2]"),
    ])
    publisher = AgentEventPublisher("r1", "c1")
    token = set_event_publisher(publisher)
    try:
        async with wms_tools(upstream_ok) as tools:
            node = InventoryAnalysisNode(subagent=InventoryAnalysisSubAgent(chat_model=model, tools=tools))
            result = await node({"user_message": "分析M001为什么不能出库，并查询库位"})
    finally:
        reset_event_publisher(token)
    assert result["status"] == "SUCCESS"
    assert "wms_query_stock" in result["answer"] and "wms_query_locations" in result["answer"]
    assert "42" in result["answer"] and "A-01" in result["answer"]
    assert next(m.content for m in model.messages if isinstance(m, HumanMessage)).startswith("分析M001")
    evidence = [json.loads(m.content) for m in model.messages if isinstance(m, ToolMessage)]
    assert evidence[0]["evidence_id"] == "E1"
    events = []
    while not publisher.queue.empty():
        events.append(publisher.queue.get_nowait())
    assert [e.event_type for e in events] == ["tool_start", "tool_end", "tool_start", "tool_end"]
    assert events[0].data["toolCallId"] == events[1].data["toolCallId"]
    assert events[2].data["toolCallId"] != events[0].data["toolCallId"]
    assert events[1].data["success"] is True
    assert events[1].data["durationMs"] >= 0


async def test_analysis_without_successful_query_does_not_repeat_model_claims():
    from wms_agent.apps.warehouse.subagents.inventory_analysis.agent import InventoryAnalysisSubAgent
    from wms_agent.apps.warehouse.agent.nodes.agent.inventory_analysis import InventoryAnalysisNode
    model = AnalysisModel([AIMessage(content="总库存999，已经冻结")])
    async with wms_tools(upstream_ok) as tools:
        node = InventoryAnalysisNode(subagent=InventoryAnalysisSubAgent(chat_model=model, tools=tools))
        result = await node({"user_message": "分析M001库存"})
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert "999" not in result["answer"]


async def test_stream_api_runs_main_graph_through_mcp_and_preserves_freeze_flow():
    from langgraph.checkpoint.memory import InMemorySaver
    from wms_agent.application import create_app
    from wms_agent.config import Settings
    from wms_agent.apps.warehouse.container import create_warehouse_container
    from wms_agent.apps.warehouse.agent.state.agent_intent import IntentResult
    from test_modular_runtime import Inventory, Audit
    from types import SimpleNamespace

    class IntentModel:
        async def ainvoke(self, messages):
            return IntentResult(intent="INVENTORY_ANALYSIS", confidence=1, material_code="M001")

    class FullModel(AnalysisModel):
        def with_structured_output(self, *args, **kwargs):
            return IntentModel()

    model = FullModel([AIMessage(content="", tool_calls=[
        {"id": "stock", "name": "wms_query_stock", "args": {"material_code": "M001"}},
        {"id": "loc", "name": "wms_query_locations", "args": {"material_code": "M001"}},
    ]), AIMessage(content="可用12，预占20，冻结10；A-01库位12。[E1][E2]")])

    async with wms_tools(upstream_ok) as tools:
        inventory = Inventory()
        warehouse = create_warehouse_container(inventory_client=inventory, location_client=inventory,
            chat_model=model, checkpointer=InMemorySaver(), audit_service=Audit(), analysis_tools=tools)

        @asynccontextmanager
        async def runtime_factory(settings):
            yield SimpleNamespace(warehouse=warehouse)

        app = create_app(Settings(), runtime_factory=runtime_factory)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://agent") as client:
                response = await client.post("/api/agent/chat/stream", json={
                    "conversationId": "mcp-stream", "message": "分析M001库存，并查看库位"})
                assert response.status_code == 200
                events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
                assert events[-1]["eventType"] == "done"
                assert events[-1]["status"] == "SUCCESS"
                assert "42" in events[-1]["data"]["answer"]
                assert "A-01" in events[-1]["data"]["answer"]
                assert len({e["requestId"] for e in events}) == 1
                ends = [e for e in events if e["eventType"] == "tool_end"]
                assert len(ends) == 2 and all(e["data"]["transport"] == "mcp" for e in ends)
                assert ends[0]["data"]["output"]["data"]["available_qty"] == 12
                # 固定冻结链仍用原 HTTP port，不能误调用 MCP 写工具。
                started = await client.post("/api/workflow/freeze/start", json={
                    "threadId": "mcp-freeze", "materialCode": "M001", "quantity": 5})
                assert started.json()["status"] == "WAITING_APPROVAL"
                approved = await client.post("/api/workflow/freeze/resume", json={
                    "threadId": "mcp-freeze", "approved": True, "approverId": "u1"})
                assert approved.json()["status"] == "SUCCESS"
                assert inventory.executions == ["FREEZE_INVENTORY:mcp-freeze"]
