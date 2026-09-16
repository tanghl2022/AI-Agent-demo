from wms_agent.apps.warehouse.agent.tool_execution_tracker import ToolExecutionTracker


def test_parallel_runs_have_independent_duration():
    now = [0.0]
    tracker = ToolExecutionTracker(clock=lambda: now[0])
    tracker.start("fast")
    tracker.start("slow")
    now[0] = 0.05
    assert tracker.finish("fast") == 50
    now[0] = 2.0
    assert tracker.finish("slow") == 2000
    assert tracker.finish("missing") is None
