"""WMS 接入配置，不包含仓储业务规则。"""
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class WmsSettings:
    base_url: str = "http://127.0.0.1:8080"
    timeout: float = 10.0

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if url.scheme not in {"http", "https"} or not url.netloc:
            raise ValueError("WMS_SERVICE_BASE_URL 必须是 HTTP 地址")
        if self.timeout <= 0:
            raise ValueError("WMS_SERVICE_TIMEOUT 必须大于零")
