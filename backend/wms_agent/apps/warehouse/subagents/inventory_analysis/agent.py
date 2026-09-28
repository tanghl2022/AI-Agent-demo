"""有界只读分析循环：事实来自工具，结果附确定性的证据清单。"""
import asyncio
import json
from dataclasses import dataclass
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from .prompt import INVENTORY_ANALYSIS_SYSTEM_PROMPT
from .tool_runner import execute_tool


@dataclass(frozen=True)
class AnalysisResult:
    answer: str
    status: str
    evidence: list[dict]


def evidence_summary(evidence: list[dict]) -> str:
    lines = []
    for item in evidence:
        data = item["data"]
        if "locations" in data:
            locations = data["locations"]
            facts = "；".join(f"{loc['location_code']}：{loc.get('quantity') if loc.get('quantity') is not None else '数量未知'}"
                             for loc in locations[:20]) or "未返回库位"
            if len(locations) > 20:
                facts += f"；另有 {len(locations) - 20} 个库位，完整数据见工具结果"
        else:
            facts = "，".join(f"{label} {data.get(key, data.get(alias, '未知'))}" for label, key, alias in [
                ("总库存", "total_qty", "totalQty"), ("预占", "reserved_qty", "reservedQty"),
                ("冻结", "frozen_qty", "frozenQty"), ("可用", "available_qty", "availableQty")])
        lines.append(f"[{item['id']}] {item['tool']} · {data.get('material_code', data.get('materialCode', ''))}：{facts}"
                     f"（{item['meta']['source']}，{item['meta']['queried_at']}）")
    return "\n\n查询依据：\n" + "\n".join(lines) if lines else ""


class InventoryAnalysisSubAgent:
    def __init__(self, *, chat_model: Any, tools: list, max_iterations: int = 8,
                 max_tool_calls: int = 16, tool_timeout: float = 20, model_timeout: float = 60):
        self._tools = tools
        self._tool_map = {tool.name: tool for tool in tools}
        self._chat_model = chat_model
        self._max_iterations = max_iterations
        self._max_tool_calls = max_tool_calls
        self._tool_timeout = tool_timeout
        self._model_timeout = model_timeout

    async def ainvoke(self, question: str) -> str:
        """保留已有直接调用方的字符串返回契约。"""
        return (await self.analyze(question)).answer

    async def analyze(self, question: str) -> AnalysisResult:
        if not question.strip():
            return AnalysisResult("请提供需要分析的库存问题。", "CLARIFICATION_REQUIRED", [])
        model = self._chat_model.bind_tools(self._tools)
        messages = [SystemMessage(content=INVENTORY_ANALYSIS_SYSTEM_PROMPT), HumanMessage(content=question)]
        evidence: list[dict] = []
        failures: list[str] = []
        calls = 0

        def finish(answer: str, status: str) -> AnalysisResult:
            if failures:
                answer += "\n\n未完成的查询：" + "；".join(dict.fromkeys(failures)) + "。这些数据不能用于确定结论。"
            return AnalysisResult(answer + evidence_summary(evidence), status, evidence)

        for _ in range(self._max_iterations):
            try:
                async with asyncio.timeout(self._model_timeout):
                    response = await model.ainvoke(messages)
            except Exception:
                return finish("分析模型调用失败；请依据已完成的查询核实，稍后重试。", "SYSTEM_FAILED")
            messages.append(response)
            if not response.tool_calls:
                if not evidence:
                    return finish("尚未取得有效查询证据，无法判断库存或库位情况。请补充明确的物料编码或稍后重试。",
                                  "INSUFFICIENT_EVIDENCE")
                return finish(str(response.content), "PARTIAL" if failures else "SUCCESS")
            for call in response.tool_calls:
                if calls >= self._max_tool_calls:
                    return finish("已达到工具调用上限，当前调查尚未完成。", "INSUFFICIENT_EVIDENCE")
                calls += 1
                name = call["name"]
                result = await execute_tool(self._tool_map.get(name), name, call["args"], timeout=self._tool_timeout)
                if result["success"]:
                    evidence_id = f"E{len(evidence) + 1}"
                    evidence.append({"id": evidence_id, "tool": name, "data": result["data"], "meta": result["meta"]})
                    result = {**result, "evidence_id": evidence_id}
                else:
                    failures.append(f"{name}：{result['error']['message']}")
                messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
        return finish("库存分析超过最大推理轮次，当前调查尚未完成。", "INSUFFICIENT_EVIDENCE")
