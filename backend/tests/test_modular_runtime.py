"""验证模块装配后的真实流程和离线应用生命周期。"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from wms_agent.application import create_app
from wms_agent.config import Settings, load_settings
from wms_agent.apps.warehouse.container import create_warehouse_container
from wms_agent.apps.warehouse.models.query import StockQueryResult, LocationQueryResult
from wms_agent.apps.warehouse.models.freeze import WmsFreezeResult


class Inventory:
    """只替换外部系统，图、服务与 API 使用实际实现。"""

    def __init__(self):
        self.executions = []

    async def query_stock(self, material_code):
        return StockQueryResult(material_code, 100, 0, 0, 100)

    async def query_locations(self, material_code):
        return LocationQueryResult(material_code, [])

    async def freeze_inventory(self, *, idempotency_key, material_code, quantity):
        self.executions.append(idempotency_key)
        return WmsFreezeResult(True, True, idempotency_key, material_code, quantity,
                               100, 0, quantity, 100 - quantity, "冻结成功")


class Audit:
    def __init__(self):
        self.records = []

    async def record_freeze_approval(self, *, thread_id, state):
        self.records.append((thread_id, state["approved"]))
        return True


class Model:
    def with_structured_output(self, *args, **kwargs):
        return self

    async def ainvoke(self, messages):
        from wms_agent.apps.warehouse.agent.state.agent_intent import IntentResult
        return IntentResult(intent="QUERY_STOCK", confidence=1.0, material_code="MAT001")


def make_warehouse(model=None):
    inventory, audit = Inventory(), Audit()
    warehouse = create_warehouse_container(
        inventory_client=inventory, location_client=inventory,
        chat_model=model or Model(), checkpointer=InMemorySaver(), audit_service=audit,
    )
    return warehouse, inventory, audit


@pytest.mark.asyncio
async def test_new_chat_request_starts_a_separate_business_workflow():
    from wms_agent.apps.warehouse.agent.state.agent_intent import IntentResult

    class FreezeModel(Model):
        async def ainvoke(self, messages):
            return IntentResult(intent="FREEZE_INVENTORY", confidence=1.0, material_code="MAT001", quantity=5)

    warehouse, _, _ = make_warehouse(FreezeModel())
    first = await warehouse.agent_service.chat("c-freeze", "冻结5个")
    second = await warehouse.agent_service.chat("c-freeze", "再申请冻结5个")
    assert first["status"] == second["status"] == "WAITING_APPROVAL"
    assert first["workflow_instance_id"] != second["workflow_instance_id"]


@pytest.mark.asyncio
async def test_approval_executes_and_rejection_does_not():
    warehouse, inventory, audit = make_warehouse()
    service = warehouse.freeze_workflow_service
    started = await service.start(thread_id="freeze-one", material_code="MAT001", quantity=20)
    assert started["status"] == "WAITING_APPROVAL"
    assert started["interrupts"]
    assert inventory.executions == []
    approved = await service.resume(thread_id="freeze-one", approved=True, approver_id="U1")
    assert approved["status"] == "SUCCESS"
    assert approved["finalAvailableQty"] == 80
    assert approved["idempotencyKey"] == "FREEZE_INVENTORY:freeze-one"
    await service.start(thread_id="freeze-two", material_code="MAT001", quantity=30)
    rejected = await service.resume(thread_id="freeze-two", approved=False, approver_id="U2")
    assert rejected["status"] == "CANCELLED"
    assert inventory.executions == ["FREEZE_INVENTORY:freeze-one"]
    assert audit.records == [("freeze-one", True), ("freeze-two", False)]


@pytest.mark.asyncio
async def test_duplicate_workflow_keeps_original_request_and_completed_result():
    warehouse, inventory, _ = make_warehouse()
    service = warehouse.freeze_workflow_service
    await service.start(thread_id="freeze-retry", material_code="MAT001", quantity=20)
    with pytest.raises(ValueError, match="其他冻结申请"):
        await service.start(thread_id="freeze-retry", material_code="MAT001", quantity=30)
    await service.resume(thread_id="freeze-retry", approved=True, approver_id="U1")
    repeated = await service.resume(thread_id="freeze-retry", approved=False, approver_id="U2")
    assert repeated["status"] == "SUCCESS"
    assert repeated["approved"] is True
    assert inventory.executions == ["FREEZE_INVENTORY:freeze-retry"]


@pytest.mark.asyncio
async def test_adapter_reports_rejection_instead_of_claiming_waiting():
    from wms_agent.apps.warehouse.agent.capabilities.freeze_workflow import create_freeze_workflow_adapter
    warehouse, inventory, _ = make_warehouse()
    node = create_freeze_workflow_adapter(warehouse.freeze_workflow_service)
    result = await node({"material_code": "MAT001", "quantity": 101})
    assert result["status"] == "REJECTED"
    assert "不足" in result["answer"]
    assert result["active_workflow"] is None
    assert inventory.executions == []


@pytest.mark.asyncio
async def test_insufficient_stock_never_waits_for_approval():
    warehouse, inventory, _ = make_warehouse()
    result = await warehouse.freeze_workflow_service.start(
        thread_id="freeze-low", material_code="MAT001", quantity=101,
    )
    assert result["status"] == "REJECTED"
    assert not result["success"]
    assert inventory.executions == []


def test_api_uses_isolated_runtime_and_closes_it():
    events = []

    @asynccontextmanager
    async def runtime_factory(settings):
        warehouse, _, _ = make_warehouse()
        events.append("opened")
        try:
            yield SimpleNamespace(warehouse=warehouse)
        finally:
            events.append("closed")

    app = create_app(Settings(), runtime_factory=runtime_factory)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        response = client.post("/api/agent/chat", json={"conversationId": "c1", "message": "库存"})
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"
        assert "100" in response.json()["answer"]
        stream = client.post("/api/agent/chat/stream", json={"conversationId": "c2", "message": "库存"})
        assert stream.status_code == 200
        assert "event: done" in stream.text
        stream_events = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
        request_ids = {event["requestId"] for event in stream_events}
        assert len(request_ids) == 1
        stream_state = client.get("/api/agent/checkpoint/c2").json()
        assert stream_state["values"]["request_id"] in request_ids
        assert client.get("/api/agent/checkpoint/c1").status_code == 200
        started = client.post("/api/workflow/freeze/start", json={
            "threadId": "freeze-http", "materialCode": "MAT001", "quantity": 5,
        })
        assert started.json()["status"] == "WAITING_APPROVAL"
        resumed = client.post("/api/workflow/freeze/resume", json={
            "threadId": "freeze-http", "approved": True, "approverId": "U1",
        })
        assert resumed.json()["status"] == "SUCCESS"
        assert resumed.json()["executed"] is True
    assert events == ["opened", "closed"]


def test_settings_are_read_at_call_time(monkeypatch):
    monkeypatch.setenv("WMS_SERVICE_TIMEOUT", "4.5")
    first = load_settings(load_env_file=False)
    monkeypatch.setenv("WMS_SERVICE_TIMEOUT", "8")
    second = load_settings(load_env_file=False)
    assert first.wms.timeout == 4.5
    assert second.wms.timeout == 8
