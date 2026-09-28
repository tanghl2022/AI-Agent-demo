# MCP 库存分析实施记录

目标：库存分析 Agent 通过 MCP 查询真实库存与库位，回答带查询依据，调用过程可见，错误可解释，原查询和冻结流程保持兼容。

用户已在本轮明确要求按讨论方案编写代码，直接在当前干净工作区执行，不额外创建审批轮次。

## 设计与边界

- 沿用已有 `mcp-server/wms_mcp`，改掉固定模拟库存。独立 Server 只需要 WMS HTTP，不初始化模型或 checkpoint。
- 第一版只暴露 `wms_query_stock`、`wms_query_locations`；库存分析可配置 local/mcp，默认 local 保持旧部署可用。固定查询、冻结路径不迁移。
- 使用官方 Python MCP SDK 1.30.0（v1 稳定 API），Streamable HTTP。客户端发现后创建 LangChain StructuredTool；只有两个允许工具可以执行。
- 直接使用 SDK，保留结构化结果和错误标识；避免引入适配库的额外版本耦合。每次 MCP 操作在同一异步任务内打开和关闭会话，支持并发请求隔离。
- 查询结果包含来源、时间、数据；库存分析按调用生成证据编号并附确定性的证据清单。没有成功查询时不输出模型猜测的库存结论。
- 使用现有 tool_start/tool_end SSE，增加 toolCallId 匹配；失败不伪装成成功。

## 实施步骤

- [x] 记录基线；新增真实协议/HTTP 契约测试、分析问答与事件测试，先观察失败。
- [x] 实现 Server：WMS HTTP 适配、输入/输出校验、安全错误映射、生命周期和启动入口。
- [x] 实现 Client：发现、白名单、Schema 校验、结构化响应转换、调用超时、配置和注入。
- [x] 实现分析与证据：修复 user_message 传递、工具事件、证据清单、无证据/部分失败状态。
- [x] 更新前端事件投影：同名工具通过调用 ID 配对、展示 MCP 名称和结果。
- [x] 补真实协议集成测试和操作文档；全量 Python、前端测试和构建已执行，最后一次结果见交付记录。

## 验证重点

1. HTTP 403/404/429/超时或非法 JSON 不能产生库存数据；原始服务器错误不得进入模型和页面。
2. MCP isError、格式错误、缺少工具、意外写工具均需安全失败。
3. 同名工具多次调用事件有独立 ID；取消不能被当成普通工具错误吞掉。
4. 分析入口必须收到用户问题；全部查询失败或模型未查询不能输出无依据的结论。
5. 正常查询、审批通过、拒绝和幂等回归通过。真实 Java/模型若无法访问，分别说明模拟外部边界的测试与真实联调状态。

## 环境记录

- 原 `backend/.venv` 指向另一台机器的 Python，无法使用。根 `.venv` 缺少 pytest/MCP，安装到根环境。
- 初始工作区干净；没有发现 AGENTS.md。
- 已发现分析节点读取不存在的 question 字段，以及前端测试仍引用旧版事件接口；纳入相关回归修复。
- 原参数验证节点测试遗漏 await；修正测试调用方式，未削减业务断言。
- 前端原测试使用 Vitest 2（内含 Vite 5）与现有 Vite 6 类型冲突且缺少 Node 类型；升级 Vitest 3.2.4 并补 Node 类型/ESNext.Disposable，不通过跳过类型检查掩盖问题。
- 首批 8 个 MCP 测试从缺少协议实现失败，随后仅剩分析状态失败，再到全部通过。前端同名工具/证据不足测试先失败后修复。
- 已完成独立只读代码审查，没有发现新增 P1/P2；local 旧适配器将未知库位数量记为 0 的既有行为不在本次 MCP 迁移范围。
- 真实 WMS 连通检查（提升权限后重试）返回 WinError 10061 连接拒绝，真实 Java/模型端到端联调尚未完成；不能把外部替身测试称为真实业务验收。

## 交付验证

- `.venv/Scripts/python.exe -m pytest -q`：79 passed，包含实际 MCP Streamable HTTP、主图到 API/SSE、错误路径及冻结回归。
- `.venv/Scripts/python.exe -m compileall -q backend/wms_agent mcp-server/wms_mcp`：通过。
- 前端 `npm test`：4 passed；`npm run build`：TypeScript 检查和 Vite 生产构建通过。
- `git -c core.whitespace=cr-at-eol diff --check`：通过。
- 没有修改用户 `.env`，默认 local 保持现有启动行为；启用步骤见 `mcp-server/README.md`。
