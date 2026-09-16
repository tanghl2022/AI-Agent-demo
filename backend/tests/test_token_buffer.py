from wms_agent.apps.warehouse.agent.token_buffer import TokenBuffer


def test_flush_by_size():
    now = [0.0]
    buffer = TokenBuffer(max_chars=4, max_interval=10, clock=lambda: now[0])
    buffer.append("ab")
    assert not buffer.should_flush()
    buffer.append("cd")
    assert buffer.should_flush()
    assert buffer.flush() == "abcd"
    assert not buffer.has_content()


def test_flush_by_time():
    now = [0.0]
    buffer = TokenBuffer(max_chars=100, max_interval=0.05, clock=lambda: now[0])
    buffer.append("x")
    now[0] = 0.06
    assert buffer.should_flush()
