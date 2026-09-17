import json

import httpx
from langchain_openai import ChatOpenAI

from wms_agent.apps.warehouse.agent.nodes.agent.intent_recognition import create_intent_recognition_node


async def test_deepseek_intent_request_disables_thinking():
    """通过真实 SDK 序列化检查请求，不访问远端模型。"""
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "test-completion", "object": "chat.completion", "created": 0,
            "model": "deepseek-v4-flash",
            "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "call-test", "type": "function", "function": {
                    "name": "IntentResult",
                    "arguments": json.dumps({"intent": "QUERY_STOCK", "confidence": 0.99,
                                             "material_code": "MAT001"}),
                }}],
            }}],
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        model = ChatOpenAI(
            model="deepseek-v4-flash", api_key="test-only",
            base_url="https://api.deepseek.com", http_async_client=client,
            extra_body={"thinking": {"type": "enabled"}},
            reasoning_effort="high",
        )
        node = create_intent_recognition_node(model)
        result = await node({"user_message": "查询 MAT001 库存"})

    payload = requests[0]
    assert payload["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in payload
    assert "response_format" not in payload
    assert payload["tool_choice"]["function"]["name"] == "IntentResult"
    assert result["turn_intent"] == "QUERY_STOCK"
    # 意图节点不修改调用方共享模型配置。
    assert model.extra_body == {"thinking": {"type": "enabled"}}
    assert model.reasoning_effort == "high"
