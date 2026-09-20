from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from .prompt import (
    INVENTORY_ANALYSIS_SYSTEM_PROMPT,
)
import logging

logger = logging.getLogger(__name__)

class InventoryAnalysisSubAgent:
    """
    库存异常分析 SubAgent。

    负责：
    1. 接收库存异常问题；
    2. 由 LLM 自主选择查询 Tool；
    3. 支持多轮 Tool Calling；
    4. 根据真实查询结果生成分析结论。

    注意：
    该 Agent 只允许使用只读查询 Tool。
    """

    def __init__(
        self,
        *,
        chat_model: Any,
        tools: list,
        max_iterations: int = 8,
    ):
        self._tools = tools

        # -----------------------------------------------------
        # Tool Name -> Tool
        # -----------------------------------------------------

        self._tool_map = {
            tool.name: tool
            for tool in tools
        }

        # -----------------------------------------------------
        # 将 Tool Schema 绑定给模型
        # -----------------------------------------------------

        self._model = chat_model.bind_tools(
            tools
        )

        # 防止模型无限 Tool Calling
        self._max_iterations = max_iterations

    async def ainvoke(
        self,
        question: str,
    ) -> str:
        """
        执行库存异常分析。
        """
        logger.info(
            "[InventoryAnalysisSubAgent] 开始分析，question=%s",
            question,
        )

        messages = [
            SystemMessage(
                content=INVENTORY_ANALYSIS_SYSTEM_PROMPT
            ),
            HumanMessage(
                content=question
            ),
        ]

        # =====================================================
        # Tool Calling Loop
        # =====================================================

        for iteration in range(
                1,
                self._max_iterations + 1,
        ):

            # -------------------------------------------------
            # 1. 请求 LLM
            # -------------------------------------------------
            logger.info(
                "[InventoryAnalysisSubAgent] 第 %s 轮 LLM 推理",
                iteration,
            )
            response: AIMessage = (
                await self._model.ainvoke(
                    messages
                )
            )

            messages.append(response)

            # -------------------------------------------------
            # 2. 没有 Tool Call
            #
            # 说明模型认为已经可以回答问题。
            # -------------------------------------------------

            if not response.tool_calls:
                return str(response.content)

            # -------------------------------------------------
            # 3. 执行模型请求的 Tool
            # -------------------------------------------------

            for tool_call in response.tool_calls:
                logger.info(
                    "[InventoryAnalysisSubAgent] "
                    "Tool Start: name=%s args=%s",
                    tool_name,
                    tool_args,
                )
                tool_name = tool_call["name"]

                tool_args = tool_call["args"]

                tool_call_id = tool_call["id"]

                tool = self._tool_map.get(
                    tool_name
                )

                # ---------------------------------------------
                # Tool 不存在
                # ---------------------------------------------

                if tool is None:

                    tool_result = {
                        "success": False,
                        "error": (
                            f"Tool 不存在: "
                            f"{tool_name}"
                        ),
                    }

                else:

                    try:

                        # -------------------------------------
                        # 真正执行 Tool
                        # -------------------------------------

                        tool_result = (
                            await tool.ainvoke(
                                tool_args
                            )
                        )

                    except Exception as error:

                        logger.exception(
                            "[InventoryAnalysisSubAgent] "
                            "Tool执行异常: %s",
                            tool_name,
                        )
                        # -------------------------------------
                        # Tool 异常不能让整个 Agent 崩溃
                        # -------------------------------------

                        tool_result = {
                            "success": False,
                            "error": str(error),
                        }

                # ---------------------------------------------
                # Tool Result 返回给 LLM
                # ---------------------------------------------

                messages.append(
                    ToolMessage(
                        content=str(
                            tool_result
                        ),
                        tool_call_id=tool_call_id,
                    )
                )
        logger.warning(
            "[InventoryAnalysisSubAgent] "
            "超过最大 Tool Calling 轮次: %s",
            self._max_iterations,
        )
        # =====================================================
        # 防止无限循环
        # =====================================================

        return (
            "库存异常分析超过最大工具调用轮次，"
            "当前证据不足，无法继续自动分析。"
        )