"""资源创建失败时必须关闭先前创建的资源。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from wms_agent import bootstrap
from wms_agent.config import Settings


@pytest.mark.asyncio
async def test_runtime_failure_closes_integrations_then_infrastructure(monkeypatch):
    events = []

    @asynccontextmanager
    async def infrastructure(settings):
        events.append("infra-open")
        try:
            yield SimpleNamespace(audit_pool=object(), chat_model=object(), checkpointer=object())
        finally:
            events.append("infra-close")

    @asynccontextmanager
    async def integration(settings):
        events.append("wms-open")
        try:
            yield SimpleNamespace(inventory_client=object(), location_client=object())
        finally:
            events.append("wms-close")

    def fail_assembly(**kwargs):
        raise RuntimeError("图装配失败")

    monkeypatch.setattr(bootstrap, "create_infrastructure_container", infrastructure)
    monkeypatch.setattr(bootstrap, "create_wms_integration", integration)
    monkeypatch.setattr(bootstrap, "create_warehouse_container", fail_assembly)
    with pytest.raises(RuntimeError, match="图装配失败"):
        async with bootstrap.create_runtime(Settings()):
            pytest.fail("装配失败不应产生运行时")
    assert events == ["infra-open", "wms-open", "wms-close", "infra-close"]


@pytest.mark.asyncio
async def test_wms_integration_closes_shared_http_client():
    from wms_agent.integrations.wms.container import create_wms_integration
    from wms_agent.integrations.wms.config import WmsSettings

    async with create_wms_integration(WmsSettings()) as integration:
        client = integration.inventory_client.http_client
        assert integration.location_client.http_client is client
        assert not client.is_closed
    assert client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["pool", "checkpoint"])
async def test_partial_infrastructure_failure_releases_opened_resources(monkeypatch, failure):
    from wms_agent.infrastructure import container
    events = []

    class Pool:
        def __init__(self, *args, **kwargs):
            pass

        async def open(self, *, wait):
            events.append("pool-open")
            if failure == "pool":
                raise RuntimeError("连接失败")

        async def close(self):
            events.append("pool-close")

    class Saver:
        @classmethod
        @asynccontextmanager
        async def from_conn_string(cls, uri):
            events.append("saver-open")
            try:
                yield cls()
            finally:
                events.append("saver-close")

        async def setup(self):
            raise RuntimeError("建表失败")

    monkeypatch.setattr(container, "AsyncConnectionPool", Pool)
    monkeypatch.setattr(container, "AsyncPostgresSaver", Saver)
    with pytest.raises(RuntimeError):
        async with container.create_infrastructure_container(
            Settings(llm_api_key="test-only", checkpoint_db_uri="postgresql://test/test")
        ):
            pytest.fail("资源失败后不能启动应用")
    expected = ["pool-open", "pool-close"] if failure == "pool" else [
        "pool-open", "saver-open", "saver-close", "pool-close",
    ]
    assert events == expected
