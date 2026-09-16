import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_openai")

from fastapi.testclient import TestClient
from wms_agent.application import create_app
from wms_agent.config import Settings
from contextlib import asynccontextmanager
from types import SimpleNamespace


def test_health():
    @asynccontextmanager
    async def runtime(settings):
        # 健康检查不需要真实模型或数据库。
        yield SimpleNamespace()

    with TestClient(create_app(Settings(), runtime_factory=runtime)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
