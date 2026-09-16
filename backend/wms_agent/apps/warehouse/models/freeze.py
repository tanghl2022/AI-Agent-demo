from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WmsFreezeResult:
    """库存服务返回的冻结执行结果，真实与模拟客户端共用。"""

    success: bool
    executed: bool
    idempotency_key: str
    material_code: str
    freeze_quantity: int
    total_qty: int | None
    reserved_qty: int | None
    frozen_qty: int | None
    available_qty: int | None
    message: str
