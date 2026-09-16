"""在应用创建时读取配置，测试可直接构造 Settings。"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
from wms_agent.integrations.wms.config import WmsSettings


@dataclass(frozen=True, slots=True)
class Settings:
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = field(default="", repr=False)
    llm_model: str = "gpt-4o-mini"
    checkpoint_db_uri: str = field(default="", repr=False)
    audit_db_uri: str = field(default="", repr=False)
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    wms: WmsSettings = field(default_factory=WmsSettings)

    def validate_runtime(self) -> None:
        """仅在启动真实运行时时验证必需配置。"""
        if not self.checkpoint_db_uri:
            raise ValueError("请配置 CHECKPOINT_DB_URI")
        if not self.llm_api_key:
            raise ValueError("请配置 LLM_API_KEY，兼容服务可使用其要求的占位值")


def load_settings(*, load_env_file: bool = True) -> Settings:
    if load_env_file:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI", ""),
        audit_db_uri=os.getenv("AUDIT_DB_URI", ""),
        cors_origins=tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()),
        wms=WmsSettings(base_url=os.getenv("WMS_SERVICE_BASE_URL", "http://127.0.0.1:8080"),
                        timeout=float(os.getenv("WMS_SERVICE_TIMEOUT", "10"))),
    )
