from dataclasses import dataclass


def build_freeze_idempotency_key(
    thread_id: str,
) -> str:
    """
    生成库存冻结业务幂等键。

    相同 Workflow Thread 必须生成相同 Key。
    """

    if not thread_id:
        raise ValueError(
            "thread_id不能为空"
        )

    return (
        f"FREEZE_INVENTORY:{thread_id}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FreezeExecutionResult:
    """
    库存冻结执行结果。
    """

    # 业务是否成功
    success: bool

    # 本次请求是否真正执行了冻结
    executed: bool

    # 幂等键
    idempotency_key: str

    # 返回信息
    message: str


class FreezeExecutionService:
    """
    库存冻结执行服务。

    V5.2-B：
    先使用 PostgreSQL 幂等记录 +
    Mock WMS Freeze 验证机制。

    注意：
    当前仍然不是最终生产实现。
    """

    def __init__(
        self,
        connection,
    ):
        self.connection = connection

    async def execute(
        self,
        *,
        thread_id: str,
        material_code: str,
        quantity: int,
    ) -> FreezeExecutionResult:
        """
        执行库存冻结。

        相同 idempotency_key 已经成功执行：
            不再次执行冻结，
            直接返回历史成功结果。
        """

        idempotency_key = (
            build_freeze_idempotency_key(
                thread_id
            )
        )

        # ==================================
        # 1. 查询是否已经成功执行
        # ==================================

        exists = await self._exists_success(
            idempotency_key
        )

        if exists:
            print(
                "[WMS FREEZE IDEMPOTENT HIT] "
                f"key={idempotency_key}"
            )

            return FreezeExecutionResult(
                success=True,
                executed=False,
                idempotency_key=(
                    idempotency_key
                ),
                message=(
                    "库存冻结已经执行成功，"
                    "本次为重复请求，"
                    "未再次执行冻结"
                ),
            )

        # ==================================
        # 2. Mock 真正的 WMS 冻结
        # ==================================

        print(
            "[WMS FREEZE EXECUTE] "
            f"key={idempotency_key}, "
            f"material={material_code}, "
            f"quantity={quantity}"
        )

        # 后面的 V5.3 会替换成：
        #
        # await wms_client.freeze_inventory(...)
        #
        # 当前绝对不直接 UPDATE 库存数据库。

        # ==================================
        # 3. 保存执行成功记录
        # ==================================

        await self._save_success(
            idempotency_key=(
                idempotency_key
            ),
            thread_id=thread_id,
            material_code=material_code,
            quantity=quantity,
        )

        return FreezeExecutionResult(
            success=True,
            executed=True,
            idempotency_key=(
                idempotency_key
            ),
            message=(
                f"模拟库存冻结成功，"
                f"物料={material_code}，"
                f"冻结数量={quantity}"
            ),
        )

    async def _exists_success(
        self,
        idempotency_key: str,
    ) -> bool:
        """
        查询该幂等键是否已经成功执行。
        """

        sql = """
        SELECT 1
        FROM wms_agent_operation_idempotency
        WHERE idempotency_key = %s
          AND status = 'SUCCESS'
        LIMIT 1
        """

        async with (
            self.connection.cursor()
            as cursor
        ):
            await cursor.execute(
                sql,
                (
                    idempotency_key,
                ),
            )

            row = await cursor.fetchone()

        return row is not None

    async def _save_success(
        self,
        *,
        idempotency_key: str,
        thread_id: str,
        material_code: str,
        quantity: int,
    ) -> None:
        """
        保存库存冻结成功记录。
        """

        result_data = (
            f"materialCode={material_code},"
            f"quantity={quantity}"
        )

        sql = """
        INSERT INTO
        wms_agent_operation_idempotency
        (
            idempotency_key,
            operation_type,
            thread_id,
            status,
            result_data
        )
        VALUES
        (
            %s,
            'FREEZE_INVENTORY',
            %s,
            'SUCCESS',
            %s
        )
        ON CONFLICT
        (
            idempotency_key
        )
        DO NOTHING
        """

        async with (
            self.connection.cursor()
            as cursor
        ):
            await cursor.execute(
                sql,
                (
                    idempotency_key,
                    thread_id,
                    result_data,
                ),
            )

        await self.connection.commit()