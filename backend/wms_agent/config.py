import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    cors_origins: tuple[str, ...] = tuple(filter(None, os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")))
    checkpoint_db_uri: str = os.getenv(
        "CHECKPOINT_DB_URI",
        ""
    )
    wms_service_base_url = os.getenv(
        "WMS_SERVICE_BASE_URL",
        "http://127.0.0.1:8080",
    )

    wms_service_timeout = float(
        os.getenv(
            "WMS_SERVICE_TIMEOUT",
            "10",
        )
    )

settings = Settings()
