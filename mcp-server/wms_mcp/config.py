"""独立 Server 配置；不依赖 Agent、模型或数据库。"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class ServerSettings:
    wms_url: str = "http://127.0.0.1:8080"
    timeout: float = 10
    wms_token: str = field(default="", repr=False)
    host: str = "127.0.0.1"
    port: int = 8001


def load_settings() -> ServerSettings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    return ServerSettings(
        wms_url=os.getenv("WMS_SERVICE_BASE_URL", "http://127.0.0.1:8080"),
        timeout=float(os.getenv("WMS_SERVICE_TIMEOUT", "10")),
        wms_token=os.getenv("WMS_SERVICE_TOKEN", ""),
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8001")),
    )
