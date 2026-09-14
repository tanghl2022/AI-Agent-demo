import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_openai")

from fastapi.testclient import TestClient
from wms_agent.application import create_app


def test_health():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
