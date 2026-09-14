from dataclasses import dataclass

from wms_agent.clients.contracts import InventoryClient as WmsInventoryClient


def build_freeze_idempotency_key(
    thread_id: str,
) -> str:
    """
    根据 Workflow Thread ID
    生成业务幂等Key。

    真正的幂等校验由 Java WMS Service 完成。
    """

    if not thread_id:
        raise ValueError(
            "thread_id不能为空"
        )

    return (
        f"FREEZE_INVENTORY:"
        f"{thread_id}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FreezeExecutionResult:
    """
    Agent Workflow层库存冻结结果。
    """

    success: bool

    executed: bool

    idempotency_key: str

    material_code: str

    freeze_quantity: int

    frozen_qty: int

    available_qty: int

    message: str


class FreezeExecutionService:
    """
    Agent侧库存冻结执行服务。

    V5.3：

    不直接修改库存；
    不负责最终业务幂等；
    只负责调用受控 Java WMS API。
    """

    def __init__(
        self,
        wms_inventory_client:
        WmsInventoryClient,
    ):
        self.wms_inventory_client = (
            wms_inventory_client
        )

    async def execute(
        self,
        *,
        thread_id: str,
        material_code: str,
        quantity: int,
    ) -> FreezeExecutionResult:
        """
        调用 Java WMS API 执行冻结。
        """

        idempotency_key = (
            build_freeze_idempotency_key(
                thread_id
            )
        )

        print(
            "[AGENT CALL WMS FREEZE] "
            f"key={idempotency_key}, "
            f"material={material_code}, "
            f"quantity={quantity}"
        )

        result = await (
            self
            .wms_inventory_client
            .freeze_inventory(
                idempotency_key=(
                    idempotency_key
                ),
                material_code=(
                    material_code
                ),
                quantity=quantity,
            )
        )

        print(
            "[WMS FREEZE RESULT] "
            f"success={result.success}, "
            f"executed={result.executed}, "
            f"frozenQty={result.frozen_qty}, "
            f"availableQty="
            f"{result.available_qty}"
        )

        return FreezeExecutionResult(
            success=result.success,

            executed=result.executed,

            idempotency_key=(
                result.idempotency_key
            ),

            material_code=(
                result.material_code
            ),

            freeze_quantity=(
                result.freeze_quantity
            ),

            frozen_qty=(
                result.frozen_qty
            ),

            available_qty=(
                result.available_qty
            ),

            message=result.message,
        )
