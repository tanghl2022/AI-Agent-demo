from wms_agent.models.chat_model import ChatRequest


def test_chat_request_accepts_frontend_alias():
    request = ChatRequest.model_validate({"message": "查询MAT001", "threadId": "t-1"})
    assert request.thread_id == "t-1"
