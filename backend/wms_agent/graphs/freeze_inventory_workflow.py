from datetime import datetime, timezone
from typing import Callable
from wms_agent.models.wms_query_result import StockQueryResult
from typing_extensions import TypedDict

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.types import interrupt


# ============================================================
# 1. Workflow State
# ============================================================

class FreezeInventoryState(
    TypedDict,
    total=False,
):
    """
    库存冻结工作流状态。

    注意：
    这里保存的是业务 Workflow State，
    不只是聊天 messages。

    Checkpointer 会围绕 thread_id
    对这些状态进行持久化。
    """

    """
    库存冻结 Workflow 状态。
    """

    # =========================
    # 业务申请信息
    # =========================

    material_code: str
    quantity: int
    available_qty: int

    # =========================
    # 审批状态
    # =========================

    approval_required: bool
    approved: bool

    # 审批人
    approver_id: str

    # 审批意见
    approval_remark: str

    # 审批时间，ISO-8601 格式
    approval_time: str

    # =========================
    # Workflow 状态
    # =========================

    status: str
    message: str

    thread_id: str

    final_frozen_qty: int

    final_available_qty: int

# ============================================================
# 2. prepare_freeze Node Factory
# ============================================================

def prepare_freeze_node(
    query_service,
) -> Callable:
    """
    创建库存冻结计划节点。

    使用工厂函数的原因：

    query_service 由 application.py 创建，
    再注入 Workflow。

    Workflow 本身不负责 new Service。

    类似 Spring 中：

        @Bean
        Service
            ↓
        注入 Workflow
    """

    async def node(
        state: FreezeInventoryState,
    ) -> dict:
        """
        只做：

        1. 查询实时库存
        2. 校验冻结数量
        3. 生成冻结计划

        绝对不执行库存冻结。
        """

        material_code = (
            state["material_code"]
        )

        quantity = int(
            state["quantity"]
        )

        # ====================================
        # 基础参数校验
        # ====================================

        if not material_code:

            return {
                "approval_required": False,
                "status": "REJECTED",
                "message": (
                    "物料编码不能为空"
                ),
            }

        if quantity <= 0:

            return {
                "approval_required": False,
                "status": "REJECTED",
                "message": (
                    "冻结数量必须大于0"
                ),
            }

        # ====================================
        # 查询当前实时库存
        #
        # 注意：
        # 不使用历史 ToolMessage。
        #
        # 对于库存这种实时数据，
        # 必须重新查询 WMS。
        # ====================================

        try:
            result = await query_service.query_stock(material_code)
        except Exception:
            # 查询失败时终止计划，不进入审批或执行节点。
            return {
                "approval_required": False,
                "status": "FAILED",
                "message": "库存查询失败，请稍后重试",
            }

        # ====================================
        # 查询异常处理
        # ====================================

        if not isinstance(
            result,
            StockQueryResult,
        ):

            return {
                "approval_required": False,
                "status": "FAILED",
                "message": (
                    "库存查询结果格式异常"
                ),
            }

        available_qty = result.available_qty

        # ====================================
        # 可用库存不足
        # ====================================

        if available_qty < quantity:

            return {
                "available_qty":
                    available_qty,

                "approval_required":
                    False,

                "status":
                    "REJECTED",

                "message": (
                    f"可用库存不足。"
                    f"物料={material_code}，"
                    f"当前可用库存={available_qty}，"
                    f"申请冻结数量={quantity}"
                ),
            }

        # ====================================
        # 库存充足
        #
        # 这里只生成冻结计划，
        # 下一步必须进入人工审批。
        # ====================================

        return {
            "available_qty":
                available_qty,

            "approval_required":
                True,

            "status":
                "WAITING_APPROVAL",

            "message": (
                f"冻结计划已生成。"
                f"物料={material_code}，"
                f"申请冻结={quantity}，"
                f"当前可用库存={available_qty}，"
                f"等待人工审批。"
            ),
        }

    return node


# ============================================================
# 3. Approval Node
# ============================================================

# def approval_node(
#     state: FreezeInventoryState,
# ) -> dict:
#     """
#     人工审批节点。
#
#     执行到 interrupt() 后：
#
#         Graph
#           ↓
#         暂停
#           ↓
#         Checkpoint保存
#           ↓
#         等待外部 Command(resume=...)
#
#     V5.0-A 当前只验证暂停。
#     """
#
#     approval_result = interrupt(
#         {
#             # 必须保持 JSON 可序列化。
#
#             "type":
#                 "FREEZE_INVENTORY_APPROVAL",
#
#             "title":
#                 "库存冻结审批",
#
#             "materialCode":
#                 state["material_code"],
#
#             "quantity":
#                 state["quantity"],
#
#             "availableQty":
#                 state["available_qty"],
#
#             "message": (
#                 f"申请冻结物料 "
#                 f"{state['material_code']} "
#                 f"数量 {state['quantity']}，"
#                 f"当前可用库存 "
#                 f"{state['available_qty']}，"
#                 f"是否批准？"
#             ),
#         }
#     )
#
#     # ========================================
#     # V5.0-A 首次执行实际上不会运行到这里。
#     #
#     # 下一阶段 Command(resume=True/False)
#     # 以后才会继续到这里。
#     # ========================================
#
#     return {
#         "approved":
#             bool(approval_result),
#
#         "status": (
#             "APPROVED"
#             if approval_result
#             else "REJECTED"
#         ),
#     }

def approval_node(
    state: FreezeInventoryState,
) -> dict:
    """
    人工审批节点。

    第一次执行：
        interrupt()
        ↓
        Graph暂停

    Resume：
        Command(resume=True/False)
        ↓
        interrupt()获得resume值
        ↓
        返回approved
    """

    approval_result = interrupt(
        {
            "type":
                "FREEZE_INVENTORY_APPROVAL",

            "title":
                "库存冻结审批",

            "materialCode":
                state["material_code"],

            "quantity":
                state["quantity"],

            "availableQty":
                state["available_qty"],

            "message": (
                f"申请冻结物料 "
                f"{state['material_code']} "
                f"数量 {state['quantity']}，"
                f"当前可用库存 "
                f"{state['available_qty']}，"
                f"是否批准？"
            ),
        }
    )


    return build_approval_result(
            approval_result
    )

# def execute_freeze_node(
#     state: FreezeInventoryState,
# ) -> dict:
#     """
#     执行库存冻结。
#
#     V5.0-B：
#     这里只模拟调用受控 WMS Business API。
#
#     禁止：
#         Agent直接UPDATE库存表。
#
#     生产版本必须：
#         Agent
#           ↓
#         WMS Freeze API
#           ↓
#         权限校验
#         参数校验
#         库存校验
#         状态机校验
#         幂等校验
#         事务
#           ↓
#         Inventory DB
#     """
#
#     material_code = (
#         state["material_code"]
#     )
#
#     quantity = int(
#         state["quantity"]
#     )
#
#     print(
#         "[WMS FREEZE MOCK] "
#         f"material={material_code}, "
#         f"quantity={quantity}"
#     )
#
#     return {
#         "status":
#             "SUCCESS",
#
#         "message": (
#             f"模拟库存冻结成功，"
#             f"物料={material_code}，"
#             f"冻结数量={quantity}"
#         ),
#     }

def create_execute_freeze_node(
    freeze_execution_service,
):
    """
    创建库存冻结执行节点。
    """

    async def execute_freeze_node(
        state: FreezeInventoryState,
    ) -> dict:

        result = await (
            freeze_execution_service
            .execute(
                thread_id=state[
                    "thread_id"
                ],
                material_code=state[
                    "material_code"
                ],
                quantity=int(
                    state["quantity"]
                ),
            )
        )

        return {
            "status": (
                "SUCCESS"
                if result.success
                else "FAILED"
            ),

            "message":
                result.message,

            "idempotency_key":
                result.idempotency_key,

            # 本次 HTTP 请求是否真正执行库存冻结
            "freeze_executed":
                result.executed,

            # Java实际返回的最终库存
            "final_frozen_qty":
                result.frozen_qty,

            "final_available_qty":
                result.available_qty,
        }

    return execute_freeze_node

def cancel_freeze_node(
    state: FreezeInventoryState,
) -> dict:
    """
    人工拒绝后的取消节点。

    不调用任何库存写接口。
    """

    return {
        "status":
            "CANCELLED",

        "message": (
            f"人工拒绝库存冻结申请，"
            f"物料={state['material_code']}，"
            f"申请冻结数量={state['quantity']}"
        ),
    }

# ============================================================
# 4. prepare之后路由
# ============================================================

def route_after_prepare(
    state: FreezeInventoryState,
) -> str:
    """
    库存不足 / 查询失败：

        END

    库存满足冻结条件：

        approval
    """

    if state.get(
        "approval_required"
    ):

        return "approval"

    return "end"

def route_after_approval(
    state: FreezeInventoryState,
) -> str:
    """
    根据人工审批结果决定下一步。

    approved = True
        → execute

    approved = False
        → cancel
    """

    if state.get(
        "approved",
        False,
    ):
        return "execute"

    return "cancel"

# ============================================================
# 5. 构建 Freeze Workflow
# ============================================================

def create_audit_approval_node(
    audit_service,
):
    # async def audit_approval_node(
    #     state: FreezeInventoryState,
    # ) -> dict:
    #     """
    #     保存人工审批审计记录。
    #     """
    #     print(
    #         "[AUDIT APPROVAL STATE]",
    #         state
    #     )
    #     await (
    #         audit_service
    #         .record_freeze_approval(
    #             thread_id=(
    #                 state["thread_id"]
    #             ),
    #             state=state,
    #         )
    #     )
    #
    #     return {
    #         "message": (
    #             state.get(
    #                 "message",
    #                 ""
    #             )
    #         )
    #     }
    #
    # return audit_approval_node
    async def audit_approval_node(
            state: FreezeInventoryState,
    ) -> dict:
        inserted = await (
            audit_service
            .record_freeze_approval(
                thread_id=state["thread_id"],
                state=state,
            )
        )

        print(
            "[APPROVAL AUDIT] "
            f"thread_id={state['thread_id']}, "
            f"inserted={inserted}"
        )

        return {}
    return audit_approval_node

def build_freeze_inventory_workflow(
    query_service,
    audit_service,
    freeze_execution_service,
    checkpointer,
):
    """
    构建库存冻结人工审批 Workflow。

    当前版本：

        START
          ↓
        prepare_freeze
          ↓
        是否需要审批？
        ├── 否 → END
        │
        └── 是
             ↓
          approval
             ↓
          interrupt()
             ↓
          暂停

    V5.0-B 再增加：

        approved
          ↓
        execute_freeze / cancel
    """

    builder = StateGraph(
        FreezeInventoryState
    )

    # ========================================
    # Node
    # ========================================

    builder.add_node(
        "prepare_freeze",

        prepare_freeze_node(
            query_service
        ),
    )

    builder.add_node(
        "approval",
        approval_node,
    )
    builder.add_node(
        "audit_approval",
        create_audit_approval_node(
            audit_service
        ),
    )

    builder.add_node(
        "execute_freeze",
        create_execute_freeze_node(
            freeze_execution_service
        ),
    )

    builder.add_node(
        "cancel",
        cancel_freeze_node,
    )


    # ========================================
    # Edge
    # ========================================

    builder.add_edge(
        START,
        "prepare_freeze",
    )

    builder.add_conditional_edges(
        "prepare_freeze",

        route_after_prepare,

        {
            "approval":
                "approval",

            "end":
                END,
        },
    )

    # # 当前阶段 approval 正常恢复后结束。
    # #
    # # V5.0-B 会替换成 execute/cancel。
    # builder.add_edge(
    #     "approval",
    #     END,
    # )
    # builder.add_conditional_edges(
    #     "approval",
    #
    #     route_after_approval,
    #
    #     {
    #         "execute":
    #             "execute_freeze",
    #
    #         "cancel":
    #             "cancel",
    #     },
    # )
    builder.add_edge(
        "approval",
        "audit_approval",
    )
    builder.add_conditional_edges(
        "audit_approval",
        route_after_approval,
        {
            "execute":
                "execute_freeze",

            "cancel":
                "cancel",
        },
    )
    builder.add_edge(
        "execute_freeze",
        END,
    )

    builder.add_edge(
        "cancel",
        END,
    )

    # ========================================
    # 使用已有 Checkpointer
    #
    # 现在应该是 AsyncPostgresSaver。
    # ========================================

    return builder.compile(
        checkpointer=checkpointer
    )

def build_approval_result(
    approval_result: dict,
) -> dict:
    """
    将 interrupt 恢复得到的审批数据转换为 Workflow State Update。

    注意：
    approvalTime 不相信前端传入值，
    统一由后端生成。
    """

    approved = bool(
        approval_result.get("approved")
    )

    approver_id = (
        approval_result
        .get("approverId", "")
        .strip()
    )

    remark = (
        approval_result
        .get("remark", "")
        .strip()
    )

    if not approver_id:
        raise ValueError(
            "审批人不能为空"
        )

    approval_time = (
        datetime.now(timezone.utc)
        .astimezone()
        .isoformat()
    )

    return {
        "approved":
            approved,

        "approver_id":
            approver_id,

        "approval_remark":
            remark,

        "approval_time":
            approval_time,

        "status":
            (
                "APPROVED"
                if approved
                else "REJECTED"
            ),

        "message":
            (
                "人工审批通过"
                if approved
                else "人工审批拒绝"
            ),
    }
