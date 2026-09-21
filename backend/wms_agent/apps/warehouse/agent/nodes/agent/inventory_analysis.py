import logging
from typing import Any

from wms_agent.apps.warehouse.subagents.inventory_analysis.agent import (
    InventoryAnalysisSubAgent,
)

logger = logging.getLogger(__name__)


class InventoryAnalysisNode:
    """
    库存异常分析节点。

    职责：
    1. 从 Main Graph State 获取用户问题；
    2. 调用 InventoryAnalysisSubAgent；
    3. 将分析结果写回 Graph State。

    注意：
    Node 本身不负责 Tool Calling。
    Tool Calling 属于 SubAgent 的职责。
    """

    def __init__(
        self,
        *,
        subagent: InventoryAnalysisSubAgent,
    ):
        self._subagent = subagent

    async def __call__(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:

        question = state.get(
            "question",
            ""
        )

        logger.info(
            "[InventoryAnalysisNode] "
            "开始库存分析 question=%s",
            question,
        )

        result = await self._subagent.ainvoke(
            question
        )

        logger.info(
            "[InventoryAnalysisNode] "
            "库存分析完成"
        )

        return {
            "answer": result,
        }