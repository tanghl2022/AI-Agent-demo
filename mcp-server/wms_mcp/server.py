"""独立启动：python -m wms_mcp.server；默认只监听本机。"""
from contextlib import asynccontextmanager
import httpx
from mcp.server.fastmcp import FastMCP
from wms_mcp.clients.wms_client import WmsClient
from wms_mcp.config import ServerSettings, load_settings
from wms_mcp.tools.inventory import register_inventory_tools


def create_server(settings: ServerSettings | None = None, *, http_client_factory=None) -> FastMCP:
    settings = settings or ServerSettings()
    if settings.timeout <= 0:
        raise ValueError("WMS_SERVICE_TIMEOUT 必须大于零")

    @asynccontextmanager
    async def default_client():
        headers = {"Authorization": f"Bearer {settings.wms_token}"} if settings.wms_token else {}
        async with httpx.AsyncClient(base_url=settings.wms_url.rstrip("/") + "/",
                                    timeout=settings.timeout, headers=headers, trust_env=False) as client:
            yield client

    @asynccontextmanager
    async def lifespan(server):
        async with (http_client_factory or default_client)() as client:
            yield WmsClient(client)

    server = FastMCP("wms-mcp-server", host=settings.host, port=settings.port,
                     stateless_http=True, json_response=True, lifespan=lifespan)
    register_inventory_tools(server)
    return server


def main() -> None:
    create_server(load_settings()).run(transport="streamable-http")


if __name__ == "__main__":
    main()
