import asyncio
import selectors
import sys

import uvicorn


def selector_loop_factory():
    """
    Windows 下显式创建 SelectorEventLoop。

    psycopg AsyncConnection 不支持 ProactorEventLoop，
    因此 LangGraph AsyncPostgresSaver 必须运行在 SelectorEventLoop 上。
    """
    return asyncio.SelectorEventLoop(
        selectors.SelectSelector()
    )


async def main():
    config = uvicorn.Config(
        "wms_agent.application:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )

    server = uvicorn.Server(config)

    await server.serve()


if __name__ == "__main__":
    # Runner 从 Python 3.11 起支持 loop_factory，仅 Windows 需要显式选择。
    with asyncio.Runner(loop_factory=selector_loop_factory if sys.platform == "win32" else None) as runner:
        runner.run(main())
