# WMS MCP Server

独立 Python 服务，使用官方 MCP SDK 1.30.0、Streamable HTTP `/mcp`，只提供两个只读工具：

- `wms_query_stock(material_code)`：查询库存组成。
- `wms_query_locations(material_code)`：查询库位分布。

服务通过真实 WMS HTTP API 查询，无硬编码库存、模拟数据或数据库/模型依赖。Server 将业务数据转换为结构化 `success / data / error / meta`；`meta` 记录来源与查询时间。查询时间不等于上游数据更新时间。

## 本机启动（PowerShell）

在项目根目录安装依赖（Python 3.11+）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r mcp-server/requirements.txt
```

如环境已存在，直接安装依赖即可。复制 `mcp-server/.env.example` 为 `.env`，已有配置不要覆盖，设置真实 WMS 地址。然后打开一个终端：

```powershell
cd mcp-server
../.venv/Scripts/python.exe -m wms_mcp.server
```

在 `backend/.env` 增加：

```dotenv
INVENTORY_TOOL_SOURCE=mcp
MCP_SERVER_URL=http://127.0.0.1:8001/mcp
MCP_TIMEOUT=15
```

在第二个终端从项目根目录运行：

```powershell
cd backend
../.venv/Scripts/python.exe -m wms_agent.run
```

后端原有 LLM、checkpoint、审计配置仍必需。前端按现有 `npm run dev` 启动。默认 `local` 不连接 MCP，切到 `mcp` 后必须先启动 MCP Server；发现失败会明确阻止后端启动，不静默回退。

提问：`分析 MAT001 为什么有库存却不能出库，并告诉我在哪些库位。` 请替换为实际物料。普通“查询库存”仍走现有固定查询节点，只有库存分析子 Agent 在本次范围内迁移至 MCP。

## WMS HTTP 契约

Server 请求以下两个 GET 地址（相对于 WMS_SERVICE_BASE_URL）：

```text
api/wms/inventory/{material_code}
api/wms/inventory/location/{material_code}
```

库存响应示例（仅说明字段，不是运行时默认数据）：

```json
{"materialCode":"MAT001","totalQty":42,"reservedQty":20,"frozenQty":10,"availableQty":12}
```

库位响应示例：

```json
{"materialCode":"MAT001","locations":[{"locationCode":"A-01","quantity":12}]}
```

数量要求非负整数。兼容 `locations: ["A-01"]`，未提供数量时返回 `null` 而不是 0。物料不匹配、字段缺失、非 JSON、无效数量均作为错误。当前不解包 `CommonResult`，不把 ERP 的其他库存接口假定为此契约；实际 Java 地址或字段不同时应在 `clients/wms_client.py` 做适配。

401/403/404/429、超时和网络故障返回受控错误码。错误响应中的原始正文、凭据不提供给模型或页面。Agent 只使用成功响应生成证据清单，未成功查询时不展示模型猜测的库存结论。

## 边界

- 默认只监听 127.0.0.1。该试点不实现 MCP OAuth 或用户权限系统；对外/跨主机部署必须放在受保护的入口后，不能直接公开。Java 继续执行实际权限校验。
- `WMS_SERVICE_TOKEN` 是 Server 调用 WMS 的可选服务端凭据；`MCP_ACCESS_TOKEN` 是 Agent 调用已有鉴权入口的凭据，两者不能混用。没有实现用户级委托或多租户身份传递。
- MCP 会话与会话 checkpoint 独立；客户端每次发现/调用自行初始化和关闭 MCP 会话，不跨请求共享用户上下文。
- 工具只在启动时发现，通过固定白名单和输入契约校验。增加工具需明确修改白名单、契约与测试，随后重启。
- 只读操作不自动重试、不自动回退，不暴露冻结工具。前端断开依旧遵循原取消行为。
- 回答附可核实的原始事实清单，但语言模型推断不等于自动证明；跨接口查询也不是同一事务快照。

## 验证

项目根目录执行：

```powershell
.venv/Scripts/python.exe -m pytest -q
cd frontend
npm test
npm run build
```

自动化集成测试运行真实 MCP Server、Client、Streamable HTTP 和 Agent API/SSE；只替换外部 WMS HTTP 和模型响应。真实服务验收使用有效物料提问，核对工具结果与 WMS、证据来源与时间、前端调用 ID 和耗时，再测试 WMS 不可用的错误路径。自动化测试通过不代表真实 Java/模型已联调。
