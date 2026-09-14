from fastapi import (
    APIRouter,
    Request,
)

from pydantic import (
    BaseModel,
    Field,
)

from langgraph.types import Command


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/api/workflow/freeze",
    tags=[
        "WMS Freeze Workflow"
    ],
)


# ============================================================
# Request DTO
# ============================================================

class FreezeInventoryStartRequest(
    BaseModel
):
    """
    发起库存冻结申请。
    """

    threadId: str = Field(
        min_length=1,
        description=(
            "Workflow Thread ID"
        ),
    )

    materialCode: str = Field(
        min_length=1,
        description="物料编码",
    )

    quantity: int = Field(
        gt=0,
        description="申请冻结数量",
    )


# ============================================================
# Start API
# ============================================================

@router.post(
    "/start"
)
async def start_freeze_inventory(
    body: FreezeInventoryStartRequest,
    request: Request,
):
    """
    发起库存冻结 Workflow。

    当前版本只执行到：

        prepare_freeze
            ↓
        approval
            ↓
        interrupt
            ↓
        暂停

    不执行真正的库存冻结。
    """

    # ========================================
    # 从FastAPI Application获取Workflow
    # ========================================

    workflow = request.app.state.freeze_inventory_workflow

    # ========================================
    # Checkpoint配置
    #
    # threadId 是恢复Workflow的关键。
    # ========================================

    config = {
        "configurable": {
            "thread_id":
                body.threadId
        }
    }

    # ========================================
    # 执行Workflow
    #
    # 执行到 interrupt() 后会暂停。
    # ========================================

    result = await workflow.ainvoke(
        {
            "thread_id":
                body.threadId,

            "material_code":
                body.materialCode,

            "quantity":
                body.quantity,
        },
        config=config,
    )

    # ========================================
    # 解析 Interrupt
    # ========================================

    interrupts = result.get(
        "__interrupt__",
        [],
    )

    interrupt_result = []

    for item in interrupts:

        interrupt_result.append(
            {
                # 不同LangGraph版本对象结构
                # 可能存在细微差异，
                # 所以这里安全获取。
                "id": getattr(
                    item,
                    "id",
                    None,
                ),

                "value": getattr(
                    item,
                    "value",
                    None,
                ),
            }
        )

    # ========================================
    # 如果存在 interrupt：
    #
    # Workflow 当前处于等待人工审批状态。
    # ========================================

    if interrupt_result:

        return {
            "success": True,

            "status":
                "WAITING_APPROVAL",

            "threadId":
                body.threadId,

            "interrupts":
                interrupt_result,
        }

    # ========================================
    # 如果没有中断：
    #
    # 可能是：
    # - 库存不足
    # - 参数/查询业务校验未通过
    # ========================================

    return {
        "success": (
            result.get("status")
            not in {
                "FAILED",
                "REJECTED",
            }
        ),

        "status":
            result.get(
                "status"
            ),

        "threadId":
            body.threadId,

        "message":
            result.get(
                "message"
            ),

        "availableQty":
            result.get(
                "available_qty"
            ),
    }

class FreezeInventoryResumeRequest(
    BaseModel
):
    """
    人工审批请求。
    """

    threadId: str = Field(
        min_length=1,
    )

    approved: bool

    approverId: str = Field(
        min_length=1,
        max_length=64,
    )

    remark: str = Field(
        default="",
        max_length=1000,
    )



@router.post(
    "/resume"
)
async def resume_freeze_inventory(
    body: FreezeInventoryResumeRequest,
    request: Request,
):
    """
    恢复被 interrupt 暂停的库存冻结 Workflow。
    """

    workflow = (
        request
        .app
        .state
        .freeze_inventory_workflow
    )

    # ========================================
    # 必须使用发起申请时相同的 thread_id
    # ========================================

    config = {
        "configurable": {
            "thread_id":
                body.threadId
        }
    }

    # ========================================
    # 恢复 Workflow
    #
    # True：
    #     approval_result = True
    #
    # False：
    #     approval_result = False
    # ========================================

    result = await workflow.ainvoke(
        Command(
            resume={
                # 业务 State 也保存 thread_id
                "thread_id": body.threadId,

                "approved":
                    body.approved,

                "approverId":
                    body.approverId,

                "remark":
                    body.remark,
            }
        ),
        config=config,
    )

    return {
        "success": (
            result.get("status")
            == "SUCCESS"
        ),

        "threadId":
            body.threadId,

        "approved":
            body.approved,

        "status":
            result.get(
                "status"
            ),

        "message":
            result.get(
                "message"
            ),

        "materialCode":
            result.get(
                "material_code"
            ),

        "quantity":
            result.get(
                "quantity"
            ),

        "availableQty":
            result.get(
                "available_qty"
            ),

        # Java实际执行后的库存
        "finalFrozenQty":
            result.get(
                "final_frozen_qty"
            ),

        "finalAvailableQty":
            result.get(
                "final_available_qty"),
        "idempotencyKey":
            result.get(
                "idempotency_key"
            ),

        "executed":
            result.get(
                "freeze_executed"
            ),

    }