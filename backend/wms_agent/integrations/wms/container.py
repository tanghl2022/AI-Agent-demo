from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
import httpx
from .config import WmsSettings
from .inventory_client import WmsInventoryClient
from .location_client import WmsLocationClient


@dataclass(frozen=True, slots=True)
class WmsIntegrationContainer:
    inventory_client: WmsInventoryClient
    location_client: WmsLocationClient


@asynccontextmanager
async def create_wms_integration(settings: WmsSettings) -> AsyncIterator[WmsIntegrationContainer]:
    """模块拥有 HTTP 连接池，所有客户端共享并由本上下文关闭。"""
    async with httpx.AsyncClient(
        base_url=settings.base_url.rstrip("/") + "/", timeout=settings.timeout, trust_env=False,
    ) as http_client:
        yield WmsIntegrationContainer(WmsInventoryClient(http_client), WmsLocationClient(http_client))
