from wms_agent.nodes.workflow.freeze_workflow_adapter import (
    create_freeze_workflow_adapter,
)


class FakeFreezeWorkflow:
    """
    模拟已有的 Freeze Workflow。

    Task 7 单元测试不真正：
        - 访问PostgreSQL
        - 调用Java WMS
        - 执行interrupt

    这里只验证：

        AgentState
            ↓
        Freeze Workflow

    的适配是否正确。
    """

    def __init__(self):
        self.received_input = None
        self.received_config = None

    async def ainvoke(
        self,
        input_data,
        config,
    ):
        """
        模拟Freeze Workflow启动后的结果。

        正式Workflow在approval节点会interrupt，
        这里用WAITING_APPROVAL模拟暂停后的业务状态。
        """

        self.received_input = input_data
        self.received_config = config

        return {
            "thread_id":
                input_data["thread_id"],

            "material_code":
                input_data["material_code"],

            "quantity":
                input_data["quantity"],

            "status":
                "WAITING_APPROVAL",

            "approval_available_qty":
                90,
        }


async def test_should_start_freeze_workflow():
    """
    参数完整时：

    AgentState
        ↓
    Freeze Workflow

    应正确传递：
        thread_id
        material_code
        quantity
    """

    workflow = FakeFreezeWorkflow()

    node = create_freeze_workflow_adapter(
        workflow
    )

    state = {
        "thread_id":
            "agent-freeze-001",

        "user_message":
            "帮我冻结MAT001 30个",

        "intent":
            "FREEZE_INVENTORY",

        "material_code":
            "MAT001",

        "quantity":
            30,

        "status":
            "RUNNING",
    }

    result = await node(state)

    # ========================================================
    # 验证传给Freeze Workflow的数据
    # ========================================================

    assert workflow.received_input[
        "thread_id"
    ].startswith(
        "freeze-"
    )

    assert (
        workflow.received_input[
            "material_code"
        ]
        ==
        "MAT001"
    )

    assert (
        workflow.received_input[
            "quantity"
        ]
        ==
        30
    )

    # ========================================================
    # 验证LangGraph config中的thread_id
    # ========================================================

    assert (
        workflow.received_config[
            "configurable"
        ][
            "thread_id"
        ]
        ==
        workflow.received_input[
            "thread_id"
        ]
    )

    # ========================================================
    # 验证返回给Main Agent的状态
    # ========================================================

    assert (
        result["status"]
        ==
        "WAITING_APPROVAL"
    )

    assert (
        result["active_workflow"]
        ==
        "FREEZE_INVENTORY"
    )

    assert "审批" in result["answer"]


async def test_should_not_start_workflow_when_quantity_missing():
    """
    Adapter自身继续进行防御性校验。

    即使正常情况下Parameter Validation已经校验过，
    quantity缺失时仍不能启动高风险Workflow。
    """

    workflow = FakeFreezeWorkflow()

    node = create_freeze_workflow_adapter(
        workflow
    )

    state = {
        "thread_id":
            "agent-freeze-002",

        "intent":
            "FREEZE_INVENTORY",

        "material_code":
            "MAT001",

        "quantity":
            None,

        "status":
            "RUNNING",
    }

    result = await node(state)

    assert (
        result["status"]
        ==
        "CLARIFICATION_REQUIRED"
    )

    assert workflow.received_input is None


async def test_should_not_start_workflow_when_material_missing():
    """
    缺少物料编码也不能启动Workflow。
    """

    workflow = FakeFreezeWorkflow()

    node = create_freeze_workflow_adapter(
        workflow
    )

    state = {
        "thread_id":
            "agent-freeze-003",

        "intent":
            "FREEZE_INVENTORY",

        "material_code":
            None,

        "quantity":
            30,

        "status":
            "RUNNING",
    }

    result = await node(state)

    assert (
        result["status"]
        ==
        "CLARIFICATION_REQUIRED"
    )

    assert workflow.received_input is None
