from wms_agent.models.agent_state import AgentState


def test_should_create_agent_state():
    """
    验证主 Agent State 可以保存当前一次 Agent 执行需要的通用状态。
    """

    state: AgentState = {
        "thread_id": "agent-001",
        "user_message": "帮我冻结MAT001 30个",
        "intent": "FREEZE_INVENTORY",
        "confidence": 0.98,
        "material_code": "MAT001",
        "quantity": 30,
        "location_code": None,
        "status": "RUNNING",
        "answer": "",
        "active_workflow": "FREEZE_INVENTORY",
    }

    assert state["thread_id"] == "agent-001"
    assert state["user_message"] == "帮我冻结MAT001 30个"
    assert state["intent"] == "FREEZE_INVENTORY"
    assert state["material_code"] == "MAT001"
    assert state["quantity"] == 30
    assert state["status"] == "RUNNING"
    assert state["active_workflow"] == "FREEZE_INVENTORY"


def test_should_allow_partial_agent_state():
    """
    LangGraph 中每个 Node 通常只返回自己修改的部分状态。

    所以 AgentState 必须允许字段暂时不存在。
    """

    state: AgentState = {
        "thread_id": "agent-002",
        "user_message": "MAT001还有多少库存？",
    }

    assert state["thread_id"] == "agent-002"
    assert state["user_message"] == "MAT001还有多少库存？"

    assert "intent" not in state
    assert "quantity" not in state
    assert "answer" not in state
