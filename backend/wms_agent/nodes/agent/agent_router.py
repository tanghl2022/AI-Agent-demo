from wms_agent.models.agent_state import AgentState


# ============================================================
# LangGraph 业务节点名称
# ============================================================

ROUTE_QUERY_STOCK = "query_stock"

ROUTE_QUERY_LOCATION = "query_location"

ROUTE_FREEZE_INVENTORY = "freeze_inventory"

ROUTE_CLARIFICATION = "clarification"

ROUTE_UNKNOWN = "unknown"


def route_agent_request(
    state: AgentState,
) -> str:
    """
    根据 AgentState 进行确定性路由。

    这个函数不会调用LLM。

    LLM的职责：
        理解用户自然语言
        ↓
        输出 intent

    Router的职责：
        根据系统预定义规则
        ↓
        决定进入哪个节点

    这样可以避免 LLM 直接控制高风险业务流程。
    """

    intent = state.get("intent")

    status = state.get("status")

    # ========================================================
    # 1. 参数不足优先处理
    # ========================================================

    # 即使：
    #
    # intent = FREEZE_INVENTORY
    #
    # 但如果：
    #
    # quantity = None
    #
    # Parameter Validation Node 会产生：
    #
    # status = CLARIFICATION_REQUIRED
    #
    # 这时必须拦截，
    # 绝对不能继续进入库存冻结 Workflow。
    if status == "CLARIFICATION_REQUIRED":
        return ROUTE_CLARIFICATION

    # ========================================================
    # 2. UNKNOWN
    # ========================================================

    if status == "UNKNOWN":
        return ROUTE_UNKNOWN

    if intent == "UNKNOWN":
        return ROUTE_UNKNOWN

    # ========================================================
    # 3. 只有 RUNNING 状态才允许进入业务节点
    # ========================================================

    if status != "RUNNING":
        return ROUTE_UNKNOWN

    # ========================================================
    # 4. 查询库存
    # ========================================================

    if intent == "QUERY_STOCK":
        return ROUTE_QUERY_STOCK

    # ========================================================
    # 5. 查询库位
    # ========================================================

    if intent == "QUERY_LOCATION":
        return ROUTE_QUERY_LOCATION

    # ========================================================
    # 6. 冻结库存
    # ========================================================

    if intent == "FREEZE_INVENTORY":
        return ROUTE_FREEZE_INVENTORY

    # ========================================================
    # 7. 最终兜底
    # ========================================================

    # 所有无法识别的情况统一进入 unknown。
    #
    # 这里采用 fail closed：
    #
    # “不知道该做什么”
    #     ↓
    # 不执行
    #
    # 而不是：
    #
    # “不知道该做什么”
    #     ↓
    # 猜一个流程执行
    return ROUTE_UNKNOWN