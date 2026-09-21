from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):

    QUERY_STOCK = "QUERY_STOCK"

    QUERY_LOCATION = "QUERY_LOCATION"

    FREEZE_INVENTORY = "FREEZE_INVENTORY"

    UNKNOWN = "UNKNOWN"

    INVENTORY_ANALYSIS = "INVENTORY_ANALYSIS"


class IntentResult(BaseModel):
    """
    当前这一轮用户输入的结构化识别结果。
    """

    intent: IntentType

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    material_code: str | None = None

    quantity: int | None = None

    location_code: str | None = None