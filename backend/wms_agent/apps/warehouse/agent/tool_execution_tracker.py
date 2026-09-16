import time
from collections.abc import Callable


class ToolExecutionTracker:
    """通过 Runtime run_id 配对 Tool 开始与结束事件并计算耗时。"""

    def __init__(self, clock: Callable[[], float] = time.perf_counter):
        self._clock = clock
        self._started_at: dict[str, float] = {}

    def start(self, run_id: str) -> None:
        self._started_at[run_id] = self._clock()

    def finish(self, run_id: str) -> int | None:
        started_at = self._started_at.pop(run_id, None)
        if started_at is None:
            return None
        return max(0, int((self._clock() - started_at) * 1000))
