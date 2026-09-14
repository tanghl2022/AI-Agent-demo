import time
from collections.abc import Callable


class TokenBuffer:
    """按字符数或时间阈值批量发送 Token，降低 SSE 事件碎片。"""

    def __init__(self, max_chars: int = 20, max_interval: float = 0.05, clock: Callable[[], float] = time.perf_counter):
        self.max_chars = max_chars
        self.max_interval = max_interval
        self._clock = clock
        self._parts: list[str] = []
        self._chars = 0
        self._last_flush = self._clock()

    def append(self, content: str) -> None:
        if not content:
            return
        self._parts.append(content)
        self._chars += len(content)

    def should_flush(self) -> bool:
        if not self._parts:
            return False
        return self._chars >= self.max_chars or (self._clock() - self._last_flush) >= self.max_interval

    def flush(self) -> str:
        content = "".join(self._parts)
        self._parts.clear()
        self._chars = 0
        self._last_flush = self._clock()
        return content

    def has_content(self) -> bool:
        return bool(self._parts)
