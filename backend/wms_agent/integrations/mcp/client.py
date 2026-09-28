"""固定可信 Server 的只读工具发现与执行，连接不跨异步任务共享。"""
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import httpx
from jsonschema import Draft202012Validator, ValidationError
from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from .config import McpSettings
from .result_mapper import failure, map_result

ALLOWED_TOOLS = ("wms_query_stock", "wms_query_locations")


@asynccontextmanager
async def session(settings: McpSettings):
    headers = {"Authorization": f"Bearer {settings.token}"} if settings.token else {}
    async with httpx.AsyncClient(headers=headers, timeout=settings.timeout, trust_env=False) as http:
        async with streamable_http_client(settings.url, http_client=http) as (read, write, _):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=settings.timeout)) as client:
                await client.initialize()
                yield client


def make_tool(remote, settings: McpSettings) -> StructuredTool:
    validator = Draft202012Validator(remote.inputSchema)

    async def call(**arguments) -> dict:
        try:
            validator.validate(arguments)
            code = arguments.get("material_code")
            if not isinstance(code, str) or not code.strip() or len(code) > 128 or set(arguments) != {"material_code"}:
                return failure("INVALID_ARGUMENTS", "请提供有效的物料编码")
            async with asyncio.timeout(settings.timeout):
                async with session(settings) as client:
                    result = await client.call_tool(remote.name, arguments)
                    return map_result(result, remote.name, code)
        except ValidationError:
            return failure("INVALID_ARGUMENTS", "工具参数不符合查询要求")
        except TimeoutError:
            return failure("MCP_TIMEOUT", "MCP 查询超时，请稍后重试")
        except Exception:
            # SDK 可能用 ExceptionGroup 传播网络/协议错误；不泄漏正文或凭据。
            # CancelledError 继承 BaseException，继续向上传播。
            return failure("MCP_UNAVAILABLE", "MCP 服务不可用或协议调用失败")

    return StructuredTool.from_function(name=remote.name, description=remote.description or remote.name,
        args_schema=remote.inputSchema, coroutine=call, metadata={"transport": "mcp", "server": "wms"})


async def discover_wms_tools(settings: McpSettings) -> list[StructuredTool]:
    try:
        async with asyncio.timeout(settings.timeout):
            async with session(settings) as client:
                discovered = {}
                cursor = None
                for _ in range(20):
                    page = await client.list_tools(cursor=cursor)
                    for tool in page.tools:
                        if tool.name in ALLOWED_TOOLS:
                            if tool.name in discovered:
                                raise ValueError("工具名重复")
                            discovered[tool.name] = tool
                    cursor = page.nextCursor
                    if not cursor:
                        break
                else:
                    raise ValueError("工具列表分页超限")
        if set(discovered) != set(ALLOWED_TOOLS):
            raise ValueError("缺少必需库存工具")
        for remote in discovered.values():
            Draft202012Validator.check_schema(remote.inputSchema)
            schema = remote.inputSchema
            if schema.get("type") != "object" or set(schema.get("properties", {})) != {"material_code"} or schema["properties"]["material_code"].get("type") != "string" or schema.get("required") != ["material_code"]:
                raise ValueError("库存工具输入契约不兼容")
        return [make_tool(discovered[name], settings) for name in ALLOWED_TOOLS]
    except Exception as exc:
        raise RuntimeError("WMS MCP 工具发现失败，请检查服务地址、连接和工具契约") from exc
