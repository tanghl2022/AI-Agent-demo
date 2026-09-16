class WmsClientError(RuntimeError):
    """外部仓储能力不可用；业务层不依赖 HTTP 库的异常类型。"""
