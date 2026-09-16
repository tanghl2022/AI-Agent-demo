from wms_agent.apps.warehouse.agent.nodes.agent.parameter_validation_node import (
    validate_agent_parameters,
)


def test_freeze_inventory_should_pass_when_parameters_complete():
    """
    冻结库存：
    material_code 和 quantity 都存在时，
    可以继续后续流程。
    """

    state = {
        "intent": "FREEZE_INVENTORY",
        "material_code": "MAT001",
        "quantity": 30,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "RUNNING"
    assert result["answer"] == ""


def test_freeze_inventory_should_require_quantity():
    """
    冻结库存缺少 quantity，
    必须要求用户补充数量。
    """

    state = {
        "intent": "FREEZE_INVENTORY",
        "material_code": "MAT001",
        "quantity": None,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert "MAT001" in result["answer"]
    assert "多少" in result["answer"]


def test_freeze_inventory_should_require_material_code():
    """
    冻结库存缺少物料编码。
    """

    state = {
        "intent": "FREEZE_INVENTORY",
        "material_code": None,
        "quantity": 30,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert "物料" in result["answer"]


def test_freeze_inventory_should_reject_non_positive_quantity():
    """
    quantity <= 0 不能进入冻结流程。
    """

    state = {
        "intent": "FREEZE_INVENTORY",
        "material_code": "MAT001",
        "quantity": 0,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert "大于0" in result["answer"]


def test_query_stock_should_require_material_code():
    """
    查询库存必须有 material_code。
    """

    state = {
        "intent": "QUERY_STOCK",
        "material_code": None,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert "物料" in result["answer"]


def test_query_stock_should_pass_when_material_code_exists():
    """
    查询库存参数完整。
    """

    state = {
        "intent": "QUERY_STOCK",
        "material_code": "MAT001",
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "RUNNING"


def test_query_location_should_require_material_code():
    """
    查询库位必须有 material_code。
    """

    state = {
        "intent": "QUERY_LOCATION",
        "material_code": None,
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert "物料" in result["answer"]


def test_unknown_intent_should_not_continue():
    """
    UNKNOWN 不应该进入后续业务。
    """

    state = {
        "intent": "UNKNOWN",
    }

    result = validate_agent_parameters(state)

    assert result["status"] == "UNKNOWN"
