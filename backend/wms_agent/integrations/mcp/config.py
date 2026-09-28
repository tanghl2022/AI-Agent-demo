from dataclasses import dataclass, field
from math import isfinite
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class McpSettings:
    url: str = "http://127.0.0.1:8001/mcp"
    timeout: float = 15
    token: str = field(default="", repr=False)

    def __post_init__(self):
        parts = urlsplit(self.url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.fragment or parts.query:
            raise ValueError("MCP_SERVER_URL 必须为无凭据、无查询参数的 HTTP(S) 地址")
        if not isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("MCP_TIMEOUT 必须为有限正数")
