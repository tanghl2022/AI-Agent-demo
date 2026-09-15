from wms_agent.models.wms_freeze_result import WmsFreezeResult

import httpx

from wms_agent.models.wms_query_result import StockQueryResult


class WmsInventoryClient:
    """
    WMS库存 HTTP Client。

    Agent 不直接操作库存数据库，
    所有库存写操作必须通过 Java WMS Business API。
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
    ):
        self.base_url = (
            base_url.rstrip("/")
        )

        self.timeout = timeout


    async def query_stock(
            self,
            material_code: str,
    ) -> StockQueryResult:
        """
        查询Java WMS中的实时库存。

        查询属于只读操作，
        Agent不能直接查询MySQL，
        必须通过WMS业务API。
        """

        url = (
            f"{self.base_url}"
            f"/api/wms/inventory/{material_code}"
        )

        async with httpx.AsyncClient(
                timeout=self.timeout,
        # WMS API 是受控的内部业务服务。
        # 禁止 httpx 自动继承操作系统/环境中的 HTTP 代理配置，
        # 避免 localhost / 内网 WMS 请求被代理转发。
                trust_env=False
        ) as client:
            response = await client.get(
                url
            )

        response.raise_for_status()

        data = response.json()

        return StockQueryResult(
            material_code=data[
                "materialCode"
            ],

            total_qty=data[
                "totalQty"
            ],

            reserved_qty=data[
                "reservedQty"
            ],

            frozen_qty=data[
                "frozenQty"
            ],

            available_qty=data[
                "availableQty"
            ],
        )


    async def freeze_inventory(
            self,
            *,
            idempotency_key: str,
            material_code: str,
            quantity: int,
    ) -> WmsFreezeResult:
        """
        调用 Java WMS 库存冻结接口。

        错误分类：

        4xx：
            WMS正常业务拒绝，
            返回 success=False。

        5xx：
            WMS系统异常，
            抛出异常。

        Timeout / Connection Error：
            技术异常，
            抛出异常。
        """

        url = (
            f"{self.base_url}"
            f"/api/inventory/freeze"
        )

        request_body = {
            "idempotencyKey":
                idempotency_key,

            "materialCode":
                material_code,

            "quantity":
                quantity,
        }

        try:

            async with httpx.AsyncClient(
                    timeout=self.timeout
            ) as client:

                response = await client.post(
                    url,
                    json=request_body,
                )

        except httpx.TimeoutException as exc:

            raise RuntimeError(
                "调用WMS库存冻结接口超时"
            ) from exc

        except httpx.RequestError as exc:

            raise RuntimeError(
                f"无法连接WMS服务：{exc}"
            ) from exc

        # =========================================
        # 1. 解析Java返回JSON
        # =========================================

        try:

            data = response.json()

        except Exception as exc:

            raise RuntimeError(
                "WMS接口返回了无法解析的响应"
            ) from exc

        # =========================================
        # 2. 4xx = 正常业务拒绝
        #
        # 例如：
        # - 库存不足
        # - 物料不存在
        # - 状态不允许
        # - 参数违反业务规则
        # =========================================

        if 400 <= response.status_code < 500:
            return WmsFreezeResult(
                success=False,

                executed=False,

                idempotency_key=(
                    idempotency_key
                ),

                material_code=(
                    material_code
                ),

                freeze_quantity=(
                    quantity
                ),

                total_qty=(
                    data.get("totalQty")
                ),

                reserved_qty=(
                    data.get("reservedQty")
                ),

                frozen_qty=(
                    data.get("frozenQty")
                ),

                available_qty=(
                    data.get("availableQty")
                ),

                message=data.get(
                    "message",
                    "WMS业务执行失败",
                ),
            )

        # =========================================
        # 3. 5xx = Java WMS系统异常
        # =========================================

        if response.status_code >= 500:
            message = data.get(
                "message",
                "WMS服务内部异常",
            )

            raise RuntimeError(
                f"WMS服务异常：{message}"
            )

        # =========================================
        # 4. 正常成功响应
        # =========================================

        return WmsFreezeResult(
            success=bool(
                data.get("success")
            ),

            executed=bool(
                data.get("executed")
            ),

            idempotency_key=data.get(
                "idempotencyKey",
                idempotency_key,
            ),

            material_code=data.get(
                "materialCode",
                material_code,
            ),

            freeze_quantity=int(
                data.get(
                    "freezeQuantity",
                    quantity,
                )
            ),

            total_qty=data.get(
                "totalQty"
            ),

            reserved_qty=data.get(
                "reservedQty"
            ),

            frozen_qty=data.get(
                "frozenQty"
            ),

            available_qty=data.get(
                "availableQty"
            ),

            message=data.get(
                "message",
                "",
            ),
        )
