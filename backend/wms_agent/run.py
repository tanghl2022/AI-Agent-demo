import asyncio
import selectors

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
    # Python 3.13 支持 loop_factory
    asyncio.run(
        main(),
        loop_factory=selector_loop_factory,
    )