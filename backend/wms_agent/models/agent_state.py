from typing import TypedDict


class AgentState(TypedDict, total=False):
    """
    WMS Agent 主流程共享状态。

    V6.1开始：

    conversation_id
        Main Agent会话ID

    workflow_instance_id
        具体业务Workflow实例ID

    两者必须分离。
    """

    # ========================================================
    # 会话与请求
    # ========================================================

    conversation_id: str

    request_id: str

    user_message: str

    previous_user_message: str | None

    # ========================================================
    # 当前轮LLM识别结果
    # ========================================================

    turn_intent: str | None

    turn_confidence: float | None

    turn_material_code: str | None

    turn_quantity: int | None

    turn_location_code: str | None

    # ========================================================
    # 合并后的业务上下文
    # ========================================================

    intent: str | None

    confidence: float | None

    material_code: str | None

    quantity: int | None

    location_code: str | None

    # ========================================================
    # 多轮参数补全
    # ========================================================

    pending_intent: str | None

    missing_parameters: list[str]

    # ========================================================
    # Workflow
    # ========================================================

    active_workflow: str | None

    workflow_instance_id: str | None

    # ========================================================
    # Agent执行状态
    # ========================================================

    status: str

    answer: str

    # ==============================
    # V6.4错误信息
    # ==============================

    error_code: str | None
    error_message: str | None
    retry_count: int
    retryable: bool
    failed_node: str | None